<img src="assets/images/Omni_Banner.png" alt="OMNI" width="100%">
<p align="center">
    <a href="context/hardware.md"><img src="https://img.shields.io/badge/Hardware-Raspberry%20Pi%203B-c51a4a?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Hardware"></a>
    <a href="cloud/try_turn.py"><img src="https://img.shields.io/badge/AI%20Engine-Gemini%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"></a>
    <a href="firmware/speech.py"><img src="https://img.shields.io/badge/Speech-Vosk%20%2B%20ElevenLabs-FF6F00?style=for-the-badge" alt="Speech"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"></a>
</p>
<hr>

> [!NOTE]
> Ask Omni to generate an app, and it builds it for you in real time.
> Speak again to change that app, ask a question, or navigate the UI.

## What can Omni do?

<table align="center">
    <tr>
        <td align="center" width="240"><b>01. Voice Navigation</b></td>
        <td align="center" width="240"><b>02. Kinetic Wheel Browsing</b></td>
        <td align="center" width="240"><b>05. Generative App Genesis</b></td>
    </tr>
    <tr>
        <td align="center"><img src="assets/images/01_voice_navigation.gif" alt="Omni Voice Navigation" width="240"></td>
        <td align="center"><img src="assets/images/02_wheel_browsing.gif" alt="Omni Kinetic Wheel Browsing" width="240"></td>
        <td align="center"><img src="assets/images/05_generate_flashcards.gif" alt="Omni Generative App Genesis" width="240"></td>
    </tr>
    <tr>
        <td align="center"><sub><i>Push-to-talk voice navigation</i></sub></td>
        <td align="center"><sub><i>Rotary kinetic launcher wheel</i></sub></td>
        <td align="center"><sub><i>Dynamic micro-app compilation</i></sub></td>
    </tr>
</table>

## System architecture

Vosk turns speech into text on the device. Omni firmware sends that text and the contract to Gemini, and one structured turn comes back. ElevenLabs speaks the line. The simulator runs that same firmware before a feature ships.

```mermaid
flowchart LR
    subgraph device["Raspberry Pi"]
        direction TB
        vosk["<b>Vosk</b><br/><i>On-device AI ASR</i>"]
        omni["<b>Omni firmware</b><br/><i>Runs the apps</i>"]
        vosk --> omni
    end
    subgraph gemini["Gemini"]
        direction TB
        decide["<b>Decisions</b><br/><i>What was asked</i>"]
        apps["<b>Generating apps</b><br/><i>A structured turn</i>"]
        decide --> apps
    end
    xi["<b>ElevenLabs</b><br/><i>Cloud AI text-to-speech</i>"]
    sim["<b>Testing layer</b><br/><i>Same firmware, before the device</i>"]

    omni --> decide
    apps --> omni
    omni --> xi
    xi --> omni
    sim -.-> omni
```

## AI contract

A language model answers differently every time. The contract makes every reply a fixed shape, so the firmware follows the operation instead of the wording.

```json
{
  "op": "mutate",
  "say": "Point for Logan.",
  "actions": [{ "action": "increment", "target": "logan", "amount": 1 }]
}
```

The sentence can change. The operation is what runs. The schema is the [contract](contract/README.md).

## AI reasoning

Gemini decides what was asked before it answers. The same words can mean a new app, a change to one already on the device, a page to open, or a question.

```mermaid
flowchart TD
    ask[User asks] --> intent[Classify intent]
    intent --> create[Generate an app]
    intent --> update[Change an app]
    intent --> nav[Open a page]
    intent --> say[Answer in words]
```

## Simulator

<p align="center">
    <a href="https://github.com/LThmly/Omni/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/LThmly/Omni/tests.yml?branch=main&style=for-the-badge&label=Build" alt="Build"></a>
    <a href="sim/README.md"><img src="https://img.shields.io/badge/Simulator-macOS%20%7C%20Linux%20%7C%20Windows-blueviolet?style=for-the-badge&logo=python&logoColor=white" alt="Simulator"></a>
</p>

<p align="center">
    <img src="assets/images/simulator.png" alt="Omni simulator" width="480">
</p>

The laptop runs the same firmware as the Pi, so a feature is built and tried there before it ships to the device. The tests cover that firmware, speech, generated apps, speaker audio, and the contract. A malformed reply, or a failed Gemini call, is rejected instead of saved as an app.

```sh
sh sim/run.sh
```

## Hardware layout

<p align="center">
    <img src="assets/images/board_layout.png" alt="Raspberry Pi, display, microphone, and speaker" width="480">
</p>

The Pi, the 5" display, the microphone, and the speaker had to live in one handheld, so the shell is a top and bottom cover around that stack. The speaker is a small driver on the Pi's PWM pin, which leaves the I2S bus for the microphone.

## Prototype

<p align="center">
    <img src="assets/images/eink.png" alt="E-paper Omni prototype" width="280">
</p>

The first Omni was a smaller board: a Seeed XIAO ESP32-S3 and an e-paper panel. Partial refresh still left the screen too slow for the apps to feel real-time, so the display moved to the LCD. That firmware is on [eink-firmware](https://github.com/LThmly/Omni/tree/eink-firmware).

## Final design

<p align="center">
    <img src="assets/images/final_circuit.jpg" alt="Finished Omni board" width="280">
    <img src="assets/images/final.jpg" alt="Omni in its case" width="280">
</p>

The finished Omni is a Raspberry Pi 3 Model B, a 5" touch LCD, an I2S microphone, and a speaker on PWM. Vosk turns speech into text on the Pi, Gemini builds the app, and ElevenLabs says it back through the speaker.

## Check out Omni

<p align="center">
    <a href="TODO">Demo video</a>
    &nbsp;·&nbsp;
    <a href="https://devpost.com/software/omni-f362rd">Devpost</a>
</p>

## Team

<table align="center">
    <tr>
        <td align="center" width="180">
            <a href="https://github.com/cannon-spencer"><img src="https://github.com/cannon-spencer.png?size=80" width="40" height="40" alt="" style="border-radius: 50%;"></a>
            <br>
            <a href="https://github.com/cannon-spencer"><b>Cannon Spencer</b></a>
        </td>
        <td align="center" width="180">
            <a href="https://github.com/LThmly"><img src="https://github.com/LThmly.png?size=80" width="40" height="40" alt="" style="border-radius: 50%;"></a>
            <br>
            <a href="https://github.com/LThmly"><b>Logan Thomley</b></a>
        </td>
        <td align="center" width="180">
            <a href="https://github.com/Davis-Lester"><img src="https://github.com/Davis-Lester.png?size=80" width="40" height="40" alt="" style="border-radius: 50%;"></a>
            <br>
            <a href="https://github.com/Davis-Lester"><b>Davis Lester</b></a>
        </td>
        <td align="center" width="180">
            <a href="https://github.com/code-jasoo"><img src="https://github.com/code-jasoo.png?size=80" width="40" height="40" alt="" style="border-radius: 50%;"></a>
            <br>
            <a href="https://github.com/code-jasoo"><b>Jason Iduyan</b></a>
        </td>
    </tr>
</table>

<p align="center">
    <a href="https://xii.swamphacks.com/"><img src="assets/images/swamphacks-xii.png" alt="SwampHacks XII" width="40" height="40" style="vertical-align: middle;"></a>
    &nbsp;&nbsp;
    <a href="https://mlh.io/"><img src="assets/images/mlh.svg" alt="Major League Hacking" width="95" height="40" style="vertical-align: middle;"></a>
    <br>
    <sub>SwampHacks XII · <a href="https://mlh.io/">Major League Hacking</a></sub>
</p>
