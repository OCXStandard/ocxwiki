# Generic Prompting System - Flow Diagram

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User enters command                         │
│                    "wiki process-schema-url"                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    on_input_submitted()                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Is prompting mode active?                                     │  │
│  │   YES → _handle_prompt_input()                                │  │
│  │   NO  → _execute_command()                                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ (Not prompting)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      _execute_command()                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Parse command: ["wiki", "process-schema-url"]             │  │
│  │ 2. Separate command_parts from arguments                     │  │
│  │ 3. Call _start_generic_prompting()                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  _start_generic_prompting()                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Call _get_prompt_parameters(command_parts)                │  │
│  │ 2. Filter out already-provided arguments                     │  │
│  │ 3. If prompts needed:                                        │  │
│  │    - Initialize _prompting_state                            │  │
│  │    - Set _prompt_queue                                       │  │
│  │    - Call _show_next_prompt()                               │  │
│  │    - Return True                                             │  │
│  │ 4. Else: Return False (execute normally)                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ (Prompts needed)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   _get_prompt_parameters()                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Find command in self.commands                             │  │
│  │ 2. Get command.params (Click parameters)                     │  │
│  │ 3. For each param:                                           │  │
│  │    if hasattr(param, 'prompt') and param.prompt:            │  │
│  │      - Extract: name, prompt_text, is_password, default     │  │
│  │      - Add to prompt_params list                            │  │
│  │ 4. Return list of parameter info dicts                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     _show_next_prompt()                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Get next prompt from _prompt_queue                        │  │
│  │ 2. Update input widget:                                      │  │
│  │    - Set placeholder text                                    │  │
│  │    - Set password mode if needed                            │  │
│  │    - Show default value in prompt                           │  │
│  │ 3. Display prompt to user                                    │  │
│  │ 4. Wait for user input...                                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  User enters    │
                    │     value       │
                    └────────┬────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   _handle_prompt_input()                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Pop current prompt from _prompt_queue                     │  │
│  │ 2. Store value in _collected_values                          │  │
│  │ 3. Reset password mode                                       │  │
│  │ 4. Call _show_next_prompt()                                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  _show_next_prompt() (again)                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ If _prompt_queue is empty:                                   │  │
│  │   → All prompts collected!                                   │  │
│  │   → Call _execute_prompted_command()                         │  │
│  │ Else:                                                         │  │
│  │   → Show next prompt (loop continues)                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ (All collected)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 _execute_prompted_command()                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Get command_parts from _prompting_state                   │  │
│  │ 2. Get existing_args from _prompting_state                   │  │
│  │ 3. Build full argument list:                                 │  │
│  │    - Add existing arguments                                  │  │
│  │    - Add collected values with option flags                  │  │
│  │    - Example: ["--url", "value", "--folder", "path"]        │  │
│  │ 4. Combine: full_args = command_parts + arguments            │  │
│  │ 5. Clear prompting state                                     │  │
│  │ 6. Call _dispatch_command_with_args(full_args)               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               _dispatch_command_with_args()                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. Call dispatch_typer_command(typer_cli, args)              │  │
│  │ 2. Get result from typer execution                           │  │
│  │ 3. Display:                                                   │  │
│  │    - result.stdout (command output)                          │  │
│  │    - result.stderr (errors)                                  │  │
│  │    - result.help_text (if command failed)                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Command Executed!                               │
│                   Result shown to user                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Example Flow: User Session

```
USER ACTION                          SYSTEM RESPONSE
───────────────────────────────────────────────────────────────────────

> wiki process-schema-url           
                                    ┌─────────────────────────────────┐
                                    │ Detecting parameters...         │
                                    │ Found: url (prompt=True)        │
                                    │ Starting prompting mode...      │
                                    └─────────────────────────────────┘

                                    Process a schema for publishing.
                                    [https://default-url]:

> https://my-schema.xsd
                                    ┌─────────────────────────────────┐
                                    │ Collected: url = my-schema.xsd  │
                                    │ No more prompts needed          │
                                    │ Executing command...            │
                                    └─────────────────────────────────┘

                                    Processing schema...
                                    Schema processed successfully!
                                    [Command output shown]
```

## State Transitions

```
┌──────────────────┐
│   IDLE STATE     │  Normal command mode
│  _prompting_state│  = None
│  = None          │
└────────┬─────────┘
         │
         │ Command has prompt=True parameters
         ▼
┌──────────────────┐
│ PROMPTING STATE  │  Collecting user input
│ _prompting_state │  = {command_parts, existing_args}
│ = {...}          │  _prompt_queue = [prompt1, prompt2, ...]
│ _prompt_queue    │  _collected_values = {}
│ = [...]          │
└────────┬─────────┘
         │
         │ User enters each value
         ▼
┌──────────────────┐
│ COLLECTING STATE │  Storing values
│ _collected_values│  = {param1: value1, param2: value2, ...}
│ = {...}          │  _prompt_queue gets shorter
└────────┬─────────┘
         │
         │ All prompts collected (_prompt_queue empty)
         ▼
┌──────────────────┐
│ EXECUTING STATE  │  Building final command
│ Building args... │  Clearing state
│ Dispatching...   │  Executing command
└────────┬─────────┘
         │
         │ Command completes
         ▼
┌──────────────────┐
│   IDLE STATE     │  Back to normal
│ _prompting_state │  Ready for next command
│ = None           │
└──────────────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIApp (app.py)                           │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                    Command Execution                            │ │
│ │  - on_input_submitted()                                         │ │
│ │  - _execute_command()                                           │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                   Generic Prompting                             │ │
│ │  - _get_prompt_parameters()                                     │ │
│ │  - _start_generic_prompting()                                   │ │
│ │  - _show_next_prompt()                                          │ │
│ │  - _handle_prompt_input()                                       │ │
│ │  - _execute_prompted_command()                                  │ │
│ │  - _dispatch_command_with_args()                                │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        │ Uses
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Typer Commands (wiki_cli.py)                   │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │  @wiki.callback()                                               │ │
│ │  def main(ctx):                                                 │ │
│ │      ctx.obj['wiki_manager'] = get_wiki_manager()               │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │  @wiki.command()                                                │ │
│ │  def process_schema_url(                                        │ │
│ │      ctx: typer.Context,                                        │ │
│ │      url: Annotated[str, typer.Option(prompt=True)] = ...      │ │
│ │  ):                                                             │ │
│ │      wiki_manager = ctx.obj['wiki_manager']                     │ │
│ │      wiki_manager.process_schema(url, folder)                   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        │ Accesses
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   WikiManager (wiki_manager.py)                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │  Singleton instance shared via context                          │ │
│ │  - process_schema()                                             │ │
│ │  - publish_page()                                               │ │
│ │  - connect()                                                    │ │
│ │  - set_publish_state()                                          │ │
│ │  - get_publish_namespace()                                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

**Command:** `wiki process-schema-url --folder /custom/path`

```
INPUT: "wiki process-schema-url --folder /custom/path"
         │
         ▼
PARSE:  command_parts = ["wiki", "process-schema-url"]
        existing_args = ["--folder", "/custom/path"]
         │
         ▼
INTROSPECT: Get parameters with prompt=True
        Found: url (prompt=True)
               folder (no prompt, has default)
         │
         ▼
FILTER: Remove already-provided parameters
        url: NOT in existing_args → NEEDS PROMPT
        folder: IN existing_args → SKIP
         │
         ▼
PROMPT: Show prompt for 'url'
        "Process a schema for publishing. [default]:_"
         │
         ▼
COLLECT: User enters "https://my-schema.xsd"
        _collected_values = {url: "https://my-schema.xsd"}
         │
         ▼
BUILD: full_args = ["wiki", "process-schema-url",
                    "--url", "https://my-schema.xsd",
                    "--folder", "/custom/path"]
         │
         ▼
EXECUTE: dispatch_typer_command(typer_cli, full_args)
         │
         ▼
OUTPUT: Display command results
```

## Summary

This generic prompting system provides a **clean separation of concerns**:

1. **User Input Layer** - Collects data from user
2. **Processing Layer** - Introspects and manages prompts
3. **Execution Layer** - Runs commands with collected data
4. **Business Logic Layer** - WikiManager performs actual work

All working together seamlessly through the typer context! 🎯
