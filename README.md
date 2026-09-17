# VoxDesk AI

## AXE — Autonomous eXecution Engine

### Bilingual Conversational Desktop Agent

VoxDesk AI is an AI-powered desktop automation project designed to understand natural-language commands and safely execute controlled actions on a Windows desktop.

The core execution engine, **AXE (Autonomous eXecution Engine)**, converts user requests into structured tasks, validates those tasks, applies safety policies, requests human approval when required, executes only registered desktop tools, and independently verifies the outcome.

The current implementation focuses on the **desktop control and safety engine**. Voice interaction, Telugu language support, browser automation, and advanced perception are planned extensions.

---

## 1. Project Overview

AXE follows a controlled agent architecture:

```text
User Request
     |
     v
Natural Language Planner
     |
     v
Structured Task
     |
     v
Task Validation
     |
     v
Safety Classification
     |
     v
Human Approval
     |
     v
Controlled Tool Registry
     |
     v
Desktop Execution
     |
     v
Independent Verification
     |
     v
Task Result
     |
     v
Evaluation Metrics