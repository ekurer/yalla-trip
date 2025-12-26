# Prompt Engineering Decisions

This document outlines the prompt engineering approach for the Yalla Trip Travel Assistant.

## Architecture Overview

The system uses a **two-step LLM architecture** to separate concerns:

```
User Message → [Router/NLU] → Tool Execution (if needed) → [Response Generator] → Output
```

### Why Two Steps?

1. **Router Focus**: The first LLM call analyzes intent and extracts structured data without worrying about generating prose
2. **Generator Focus**: The second LLM call focuses purely on natural language generation with full context
3. **Debuggability**: Separating reasoning from generation makes it easier to diagnose issues

This mirrors production agent patterns used in systems like LangChain Agents and OpenAI's function calling paradigm.

---

## Chain-of-Thought Prompting

### Router Prompt

The router uses explicit step-by-step reasoning:

```
Think step by step:
1. What is the user explicitly asking for?
2. What implicit needs can we infer?
3. What do we already know from conversation history?
4. Is external data (weather) needed, or can we respond directly?
```

Forces the model to articulate each step, reducing errors in intent classification.

### Structured Output

We force JSON output with a schema to ensure:
- Predictable parsing
- Explicit intent labeling
- Clean state updates

---

## Response Generation

### Persona Design

```
PERSONA: You are a friendly, knowledgeable travel concierge named Yalla.
TONE: Warm but efficient. Enthusiastic about travel without being overly bubbly.
```

A consistent persona improves conversation coherence. The "concierge" framing sets expectations for helpful, service-oriented responses.

### Response Length Control

```
Keep responses under 150 words unless the user asks for a detailed itinerary.
For lists: use bullet points (max 5-7 items).
For narratives: use 2-3 short paragraphs.
```

LLMs tend toward verbose responses — explicit length guidance prevents wall-of-text outputs.

### Evidence Grounding

```
When weather data is provided, integrate it naturally into recommendations.
DO NOT dump raw forecast data. Summarize relevantly.
Example: "Pack layers - Tokyo will be cold (5-10°C) with occasional rain next week."
```

External data should enhance responses, not overwhelm them.

---

## Hallucination Prevention

### Explicit Guards

```
CRITICAL: Never invent:
- Specific prices or costs
- Flight times or schedules  
- Opening hours of attractions
- Visa requirements

If asked, recommend checking official sources or booking platforms.
```

Travel misinformation can have real consequences. We prevent the most dangerous hallucination categories explicitly.

### Alternatives Considered

1. **RAG with real data**: Would require maintaining databases of prices/schedules — too complex for this scope
2. **Blanket disclaimers**: Hurts UX; we use targeted guards instead
3. **Temperature=0**: Reduces creativity too much for travel advice

---

## Context Management

### Conversation History

We pass the last N turns (configurable) to the response generator:

```python
response_messages.extend(state.history[-settings.CONTEXT_WINDOW_TURNS:])
```

Trade-offs:
- Keeps context focused, avoids irrelevant old context
- Respects token limits
- Very long conversations may lose early context

### Structured State

Alongside raw history, we maintain explicit state:

```python
class TripSpec:
    destination: str
    start_date: str
    travelers: str

class UserProfile:
    budget: str
    pace: str
    interests: list
```

Structured state survives history truncation. Even if we forget the exact phrasing of "I want a cheap trip", we preserve `budget: "low"`.

---

## Tool Integration

### When to Call Tools

```
Use weather tool ONLY when:
1. Intent is 'packing' or 'attractions' 
2. AND destination is known

Otherwise: rely on LLM knowledge
```

Weather is time-sensitive → always fetch fresh. General travel advice is static → LLM knowledge is sufficient.

### Blending External Data

We inject tool output into the system prompt for the response generator:

```python
Tool Output (Weather): {tool_output}
```

The LLM naturally incorporates this into its response. We don't force specific formatting — the prompt guides style.

---

## Error Handling

### Unclear User Input

When the router can't determine intent and destination is unknown:

```
If intent == "chat" and no destination:
    Guide user with: "I'd love to help plan your trip! 
    Where are you thinking of going?"
```

### API Failures

```python
except Exception as e:
    tool_output = f"System: Could not fetch weather for {dest}."
```

The response generator sees the failure and handles it naturally:
> "I couldn't fetch the current weather, but generally Paris in April..."

### JSON Parsing Failures

```python
except json.JSONDecodeError:
    return {}  # Empty dict triggers fallback behavior
```

Graceful degradation over hard failures — the agent continues with reduced capability rather than crashing.
