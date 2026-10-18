# Local voice commands

These commands run after Vosk finishes the utterance, without Gemini or a network connection. The simulator and Pi share the same matcher. Omni animates its response before applying settings, editing apps, or navigating. The existing 1.2-second reading pause and wheel transitions still apply.

| Task | Examples |
| --- | --- |
| Open pages | “Open settings”, “Launch my notebook”, “Bring up the calculator”, “Take me home”, “Go to the app drawer”, “Pull up my counter application” |
| Return | “Go back”, “Close this app”, “Return to the main agent screen” |
| Theme | “Switch to light mode”, “Change the system color scheme to dark”, “Turn off dark mode”, “Enable night mode”, “Toggle the theme” |
| Animations | “Enable animations”, “Turn motion effects off”, “Enable reduced motion”, “Toggle animations” |
| Text size | “Make the font bigger”, “Use large text”, “Make text smaller”, “Reset text size” |
| Clock format | “Use twelve hour time”, “Set the clock to twenty four hour format”, “Use military time”, “Toggle clock format” |
| Preview delay | “Set preview wait to three seconds”, “Change demo wait to ten seconds”, “Set preview delay to twenty seconds” (offline app-generation demo only) |
| Time and date | “What time is it?”, “Tell me the time”, “What day is today?”, “What's today's date?” Uses the device's clock and timezone. |
| Notes | “Take a note that Buy Milk”, “Write a note Call Alex tomorrow”, “Add to my notes Pick up the parcel”, “Read my notes” |
| Arithmetic | “Calculate twenty five times four”, “What's four plus five?”, “Compute one hundred and two divided by three”, “Calculate one point five times two”, “Work out negative five plus seven” |
| Existing app buttons | “Press the increase button in counter”, “Run reset in counter”. Uses the button label and existing app name; only declared actions run. |
| Existing lists | “Add Milk and Eggs to my shopping list”. Requires one matching existing app with one declared append action. |

Navigation supports combinations of open/open up, launch, start, load, bring up, pull up, go to/into, head to, jump to, navigate to, take/bring/get me to, show me, return to, and switch (over) to. Targets accept page/screen/app/application/view suffixes. Built-in aliases include preferences/device settings/system settings, notebook/notepad, clock/digital clock, calculator/calc/math, agent/home/assistant, and wheel/launcher/app drawer/app selector. Generated apps match their exact title or ID. Polite prefixes such as “Please”, “Could you please”, and “Hey Omni” work too.

Notes append to the built-in Notes app and then open it. Calculations support addition, subtraction, multiplication, division, parentheses, negative values, digits, and spoken numbers (including hundreds, thousands, and decimals); the result opens Calculator. Time/date questions and reading notes stay on the agent page. Settings persist across restarts.

Commands are matched as complete requests. Ambiguous names, unknown tasks, questions about how to use a setting, negations, and multi-task instructions fall through to Gemini. The matcher does not infer unsupported hardware controls, timers, reminders, or new generated apps. Dictated note/list content stays data; it is not executed as another command. List operations still enforce the shared app contract and size limits.

Theme matching also handles observed Vosk variants within explicit commands, including “changed the theme to lighten mode” and “switch to dark mine”. These corrections are restricted to complete theme-command syntax; they do not rewrite arbitrary dictation or questions.
