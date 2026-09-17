# 🎙️ VoxDesk AI

### Agentic Voice-Controlled Desktop Automation Assistant for Windows

VoxDesk AI is an **agentic voice-controlled desktop automation system** that allows users to control Windows applications using natural-language voice commands.

Instead of directly executing every command, VoxDesk AI follows an agentic pipeline involving **wake-word detection, speech recognition, command normalization, task planning, safety validation, controlled execution, independent verification, and voice feedback**.

> **Project Status:** 🚀 Working Prototype
> **Platform:** Windows
> **Primary Language:** Python

---

## ✨ Key Features

* 🎙️ **Wake-word activation** using OpenWakeWord
* 🗣️ **Speech-to-text** using Groq Whisper
* 🧠 **LLM-based task planning** using Groq
* 🛡️ **Safety validation and risk classification**
* 👤 **Human approval for medium-risk actions**
* 🖥️ **Windows desktop automation**
* ⌨️ **Keyboard and text automation**
* 🔢 **Calculator operations**
* 🌐 **Browser automation**
* 🔍 **Independent action verification**
* 🔊 **Text-to-speech responses**
* 🔄 **Multi-step task execution**
* 🧪 **Unit and workflow testing**

---

## 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │     Microphone      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Wake Word Engine  │
                         │      "Alexa"        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Audio Recorder   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Groq Whisper     │
                         │       STT           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Command Normalizer  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     AXE Planner     │
                         │  Task Decomposition│
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Safety Engine     │
                         │ Risk Classification │
                         └──────────┬──────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
                  ┌─────────────┐      ┌──────────────┐
                  │   Execute   │      │ Human        │
                  │    Action   │◄─────│ Approval     │
                  └──────┬──────┘      └──────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ Desktop     │
                  │ Tools       │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ Independent │
                  │ Verifier    │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ Windows TTS │
                  └─────────────┘
```

---

## 🧠 How VoxDesk AI Works

A typical voice interaction follows this lifecycle:

### 1. Wake Word Detection

The system continuously listens for:

```text
Alexa
```

OpenWakeWord detects the wake word before the command-processing pipeline starts.

### 2. Voice Command Capture

After detecting the wake word, VoxDesk records the user's command.

Example:

```text
Alexa...
Open Notepad and type Hello World
```

### 3. Speech Recognition

The recorded audio is transcribed using Groq Whisper.

```text
Audio
  ↓
Whisper
  ↓
"Open Notepad and type Hello World"
```

### 4. Command Normalization

The raw transcription is normalized into a form suitable for the planning layer.

### 5. Task Planning

AXE Planner converts the natural-language request into structured actions.

For example:

```text
User:
Open Notepad and type Hello World
```

can become conceptually:

```text
1. open_application("notepad")
2. type_text("Hello World")
```

### 6. Safety Validation

Before execution, the planned actions are checked against the safety engine.

Different actions can have different risk levels.

For example:

```text
Opening Notepad
       ↓
      SAFE
       ↓
Execute
```

while potentially disruptive actions such as closing applications can require approval:

```text
Close Notepad
       ↓
     MEDIUM
       ↓
Human Approval
       ↓
Execute / Cancel
```

### 7. Desktop Execution

Validated actions are executed through controlled desktop tools using Windows automation technologies.

### 8. Independent Verification

After an action executes, VoxDesk AI attempts to independently verify the resulting state.

This helps distinguish:

```text
Tool executed successfully
```

from:

```text
Expected desktop state was actually achieved
```

### 9. Voice Feedback

Finally, the assistant communicates the result using Windows text-to-speech.

---

# 🖥️ Supported Desktop Capabilities

| Capability            | Status        |
| --------------------- | ------------- |
| Notepad automation    | ✅ Working     |
| File Explorer         | ✅ Working     |
| Windows Calculator    | ✅ Working     |
| Command Prompt        | ✅ Working     |
| Browser opening       | ✅ Working     |
| Browser navigation    | ✅ Working     |
| Text typing           | ✅ Working     |
| Keyboard keys         | ✅ Working     |
| Keyboard shortcuts    | ✅ Working     |
| Multi-step tasks      | ✅ Working     |
| Application switching | ✅ Working     |
| Safety approval       | ✅ Working     |
| Safety cancellation   | ✅ Working     |
| Action verification   | ✅ Implemented |
| Wake-word activation  | ✅ Working     |
| Speech recognition    | ✅ Working     |
| Text-to-speech        | ✅ Working     |

---

# 🎤 Example Commands

VoxDesk AI can process commands such as:

```text
Alexa, open Notepad
```

```text
Alexa, open Calculator
```

```text
Alexa, open File Explorer
```

```text
Alexa, open Command Prompt
```

```text
Alexa, open Notepad and type Hello World
```

```text
Alexa, open Notepad, type Hello, press Enter, and type World
```

```text
Alexa, open Calculator and calculate 15 plus 25
```

```text
Alexa, open the browser
```

```text
Alexa, open the browser and navigate to example.com
```

---

# 🛡️ Safety Architecture

Safety is an important part of VoxDesk AI's execution pipeline.

The system does not simply allow the planner to execute arbitrary actions.

The flow is:

```text
Natural Language Command
          ↓
       Planner
          ↓
     Task Actions
          ↓
    Safety Engine
          ↓
   Risk Classification
          ↓
 ┌────────┴────────┐
 │                 │
SAFE            MEDIUM/HIGH
 │                 │
 ▼                 ▼
Execute       Human Approval
                  │
            ┌─────┴─────┐
            │           │
           YES          NO
            │           │
            ▼           ▼
         Execute      Cancel
```

This provides an additional control layer between the LLM-generated plan and actual desktop execution.

---

# 🔍 Verification

VoxDesk AI includes an independent verification layer.

The goal is to avoid treating a successful tool call as automatic proof that the intended desktop state was achieved.

For example:

```text
Action:
Open Notepad

        ↓

Tool Execution
        ↓
   Successful
        ↓
Independent Verification
        ↓
Notepad detected
        ↓
Verified ✅
```

For supported interactions, the verifier can inspect resulting application state or UI state.

---

# 🔢 Calculator Verification

Calculator operations use both programmatic calculation and Windows Calculator interaction.

Example:

```text
15 + 25
```

Expected result:

```text
40
```

The system can verify the calculator result against the expected calculation.

---

# 👤 Human Approval

Potentially disruptive actions can require explicit user approval.

Example:

```text
User:
Close Notepad
```

The system can respond:

```text
This is a medium-risk action.
This will close Notepad.
This action requires your approval.
Do you want me to continue?
```

The user can then approve or cancel the operation.

---

# 🧪 Testing

The project includes tests covering multiple components:

```text
tests/
├── test_approval.py
├── test_evaluator.py
├── test_language.py
├── test_perception.py
├── test_planner.py
├── test_safety.py
├── test_stt.py
├── test_validator.py
└── test_verifier.py
```

The desktop automation workflow has also been tested across:

* Application opening
* Application focusing
* Application switching
* Application closing
* Text input
* Keyboard keys
* Keyboard shortcuts
* Calculator operations
* Browser navigation
* Multi-step workflows
* Safety approval
* Safety cancellation
* Unsupported application rejection
* Repeated execution
* Voice-controlled execution

---

# 📁 Project Structure

```text
VoxDesk-AI/
│
├── app/
│   ├── core/
│   │   ├── agent.py
│   │   ├── approval.py
│   │   ├── executor.py
│   │   ├── graph.py
│   │   ├── planner.py
│   │   ├── runtime.py
│   │   ├── safety.py
│   │   ├── task.py
│   │   ├── tool_registry.py
│   │   ├── validator.py
│   │   └── verifier.py
│   │
│   ├── tools/
│   │   ├── applications.py
│   │   ├── browser.py
│   │   ├── calculator.py
│   │   ├── desktop.py
│   │   ├── inspect_notepad.py
│   │   └── inspect_windows.py
│   │
│   ├── voice/
│   │   ├── assistant.py
│   │   ├── language.py
│   │   ├── normalizer.py
│   │   ├── recorder.py
│   │   ├── stt.py
│   │   ├── test_wake_engine.py
│   │   ├── tts.py
│   │   └── wake_word.py
│   │
│   ├── evaluation/
│   │   ├── benchmark.py
│   │   ├── evaluator.py
│   │   └── safety_benchmark.py
│   │
│   └── main.py
│
├── config/
│
├── tests/
│
├── .gitignore
├── README.md
└── requirements.txt
```

---

# ⚙️ Technology Stack

### Programming

* Python

### AI / LLM

* Groq API
* LLM-based task planning
* Whisper speech recognition

### Voice

* OpenWakeWord
* Groq Whisper
* Windows Speech / TTS

### Desktop Automation

* PyAutoGUI
* PyWinAuto
* Windows UI Automation
* Windows API
* Process inspection with `psutil`

### Agent Architecture

* AXE Agent
* Planner
* Runtime
* Tool Registry
* Safety Engine
* Validator
* Executor
* Independent Verifier

### Testing

* Pytest
* Component-level testing
* Workflow testing
* Safety testing

---

# 🚀 Installation

## 1. Clone the Repository

```bash
git clone https://github.com/vedavamshvangala/VoxDesk-AI.git
```

```bash
cd VoxDesk-AI
```

## 2. Create a Virtual Environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a local `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
```

> **Never commit your `.env` file or API keys to GitHub.**

The repository's `.gitignore` is configured to exclude `.env`.

---

# 🎙️ Running VoxDesk AI

From the project root:

```powershell
python -m app.voice.assistant
```

The assistant will start listening for the wake word:

```text
Wake word  : alexa
Threshold  : 0.5
Sample rate: 16000
Chunk size : 1280

Listening for wake word...
Say: Alexa
```

Say:

```text
Alexa
```

Then provide a desktop command.

---

# 🔐 Security Considerations

VoxDesk AI interacts directly with the user's Windows desktop.

Therefore:

* API keys should remain in environment variables.
* `.env` should never be committed.
* Arbitrary destructive operations should not be blindly executed.
* Risk-sensitive actions should pass through the safety layer.
* Human approval should be used for actions requiring confirmation.
* Tool execution should remain controlled by the tool registry and validation layers.

---

# 📌 Design Philosophy

VoxDesk AI is designed around a simple principle:

> **An AI-generated plan should not automatically mean an unrestricted desktop action.**

The system therefore separates:

```text
Planning
   ↓
Validation
   ↓
Safety
   ↓
Execution
   ↓
Verification
```

This separation makes the system easier to test, reason about, and extend.

---

# 🔮 Future Roadmap

Potential future improvements include:

* Improved multilingual voice interaction
* More Windows application integrations
* Better UI-state verification
* Stronger task recovery
* More sophisticated action planning
* Improved error handling
* Voice interruption support
* More comprehensive desktop benchmarks
* Advanced agent evaluation
* Improved observability and execution tracing

---

# 📊 Project Highlights

VoxDesk AI demonstrates the integration of several areas of modern AI engineering:

```text
LLMs
 │
 ├── Natural Language Understanding
 │
 ├── Task Planning
 │
 ├── Tool Calling
 │
 ├── Safety / Guardrails
 │
 ├── Runtime Execution
 │
 ├── Desktop Automation
 │
 └── Independent Verification
```

It is intended as an engineering project demonstrating how an LLM-driven agent can be connected to real-world desktop actions while maintaining validation and verification layers.

---

# 👨‍💻 Author

### Vedavamsh Vangala

Computer Science & Engineering — AI & ML

GitHub:

https://github.com/vedavamshvangala

Project:

https://github.com/vedavamshvangala/VoxDesk-AI

---

# 📄 License

This project is currently provided for educational and development purposes.

A formal open-source license can be added as the project matures.
