import sys

class UI:
    def __init__(self, render_manager):
        self._render_manager = render_manager
        self._start("project.mp4")

    def _nums_to_segments(self, nums):
        nums = [num for num in nums if num.isdigit()]
        nums = [num for num in nums if int(num) < len(self._render_manager.segments)]
        return [self._render_manager.segments[int(i)] for i in nums]

    def _input_to_command(self, inp):
        if len(inp) <= 0: return False, []
        is_first_letter = not inp[0].isdigit()
        command = "r" if not is_first_letter else inp[0]
        selected = self._nums_to_segments(inp[1:].split()) if is_first_letter else self._nums_to_segments(inp.split())
        return command, selected

    def _print_segments(segments):
        for segment in segments:
            print(f"{segment['id']}: {segment['start']} -> {segment['end']}")
            print(segment['text'])
            print("---" * 25)

    def _edit_segments(segments):
        for segment in segments:
            segment['text'] = editor.edit(contents=segment['text'].encode("UTF-8")).decode("UTF-8")
        return segments

    def _main_loop(self):
        command, selected = self._input_to_command(input("(lazyshorts-py) "))
        if command == "q": # quit
            UI._exit()
        elif command == "p": # print
            UI._print_segments(selected if len(selected) > 0 else self._render_manager.segments)
        elif command == "e": # edit
            if len(selected) > 0:
                UI._print_segments(UI._edit_segments(selected))
            else:
                print("You need to give atleast one segment to edit!")
        elif command == "r": # render
            if len(selected) > 0:
                file = "short.mp4"
                self._render_manager.add_to_queue((selected, file))
                print()
                UI._print_segments(selected)
                print(f"Added {file} to the queue with the above segments!")
            else:
                print("You need to give atleast one segment to render!")
        elif command == "s": # state
            for state in self._render_manager.get_renderer_states():
                print()
                print(f"{state[0]}: {state[1]} ({state[2]})")
        elif not command:
            print("Your input cannot be empty!")
        else:
            print("Sorry, unknown command!")
        return False

    def _handle_loop(self):
        while True:
            try:
                self._main_loop()
            except KeyboardInterrupt:
               UI._exit()
    
    def _exit(code = 0, msg = ""):
        print(msg)
        sys.exit(code)
    
    def _ready(self):
        UI._print_segments(self._render_manager.segments)
        print("Preprocess done!")
        self._handle_loop()

    def _start(self, file):
        print(f"Sending {file} to preprocess: this might take a while...")
        self._render_manager.input_file = file
        self._ready()
