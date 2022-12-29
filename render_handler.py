import subprocess

from enum import Enum, auto

import srt
from datetime import timedelta

from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.fx.all import crop

import shutil

class RenderStatus(Enum):
    START = auto()
    SEGMENT_TO_CLIP = auto()
    CROP_CLIP = auto()
    END_CLIP = auto()
    SUB_CLIP = auto()
    MOVE_CLIP = auto()
    FINISH = auto()

class RenderHandler():
    def __init__(self, wdmng, video, render):
        self.wdmng = wdmng
        self._video = video
        self._segments, self._final_file = render
        self._status, self._progress = RenderStatus.START, 0
        self.states = None
    
    @property
    def state(self):
        return (self._final_file, self._status, self._progress)
    @state.setter
    def state(self, state):
        self._status = state[0]
        self._progress += state[1]
        self.states.put((self._status, self._progress))

    # NOTE: whisper can return longer timestamps than original duration...
    def _get_segment_end(self, segment):
        original = VideoFileClip(self._video)
        return segment['end'] if segment['end'] < original.end else original.end
    def _get_segment_relative_end(self, segment, last_end):
        return last_end + (self._get_segment_end(segment) - segment["start"])

    def _segment_to_clip(self, segment):
        original = VideoFileClip(self._video)
        return original.subclip(segment['start'], self._get_segment_end(segment))
    def _segment_to_sub(self, segment, i, last_end, current_end):
        original = VideoFileClip(self._video)
        return srt.Subtitle(i, 
                timedelta(seconds=last_end), 
                timedelta(seconds=current_end), 
                segment["text"])

    def _enumerate_on_segments(self, selected, f):
        end = 0
        for i, segment in enumerate(selected):
            last_end = end
            end = self._get_segment_relative_end(segment, last_end)
            f(segment, i, last_end, end)
    def _segments_to_clip_and_subs(self):
        clips = []
        subs = []
        self._enumerate_on_segments(self._segments,
                lambda segment, i, last_end, current_end: 
                    [
                        clips.append(self._segment_to_clip(segment)), 
                        subs.append(self._segment_to_sub(segment, i, last_end, current_end))
                    ]
        )
        return concatenate_videoclips(clips), subs

    def _crop_clip(clip):
        (w, h) = clip.size
        return crop(clip, x_center = w/2, y_center = h/2, width = 607, height = 1080)
    def _clip_to_file(self, clip):
        clip_file = self.wdmng.create_file("end.mp4")
        clip.write_videofile(clip_file, logger=None) 
        return clip_file
    def _overlay_end_text_on_clip(clip, end_time = 5):
        return concatenate_videoclips([clip.subclip(0, clip.end - end_time), CompositeVideoClip([clip.subclip(clip.end - end_time, clip.end), TextClip("A teljes videó megtalálható fő csatornáimon!", fontsize = 48, method = "caption", font = "Arial", color="white").set_duration(end_time).set_pos("center", "center")])])

    def _burn_in_subs_to_file(self, file, sub_file):
        subbed_file = self.wdmng.create_file("subbed.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", file, "-vf", f"subtitles={sub_file}:force_style='Alignment=2,MarginV=50,Fontsize=12'", "-c:a", "copy", subbed_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT)
        return subbed_file
    def _subs_to_file(self, subs):
        sub_file = self.wdmng.create_file("subs.srt")
        with open(sub_file, "w") as file:
            file.write(srt.compose(subs))
        return sub_file
    
    def render_file(self, queue):
        self.states = queue

        self.state = (RenderStatus.SEGMENT_TO_CLIP, .2)
        concat, subs = self._segments_to_clip_and_subs()

        self.state = (RenderStatus.CROP_CLIP, .2)
        cropped = RenderHandler._crop_clip(concat)

        self.state = (RenderStatus.END_CLIP, .2)
        end_file = self._clip_to_file(RenderHandler._overlay_end_text_on_clip(cropped))

        self.state = (RenderStatus.SUB_CLIP, .2)
        subbed_file = self._burn_in_subs_to_file(end_file, self._subs_to_file(subs))

        self.state = (RenderStatus.MOVE_CLIP, .1)
        shutil.move(subbed_file, self._final_file)

        self.state = (RenderStatus.FINISH, .1)