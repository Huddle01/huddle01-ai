<!-- Begin Banner -->
<a href="https://huddle01.com"><p align="center">
<img height=100 src="https://user-images.githubusercontent.com/34184939/167926050-f1e2db1d-49ae-4b51-bd98-68e09b45c5b1.svg"/>

</p></a>
<p align="center">
  <strong>The dRTC Infra for AI.</strong>
</p>

<!-- End Banner -->

# Overview 🚀
This repository aims to bridge the gap between Artificial Intelligence (AI) and Real-Time Communication (RTC) technologies. It provides a set of examples and tutorials to help developers integrate AI into their WebRTC applications. 

# Features 🎯
- **Agents**: AI-powered agents that can be integrated into WebRTC applications, such as chatbots, voicebots, and video bots.

- **LLM Models**: API for integrating Large Language Models (LLM) into WebRTC applications, such as Realtime API, Text-to-Speech, and Speech-to-Text.

# Quick Start 🚀

To install the core Agents library:
```bash
pip install ai01
```

Internally the Library uses `huddle01-ai` package to interact with the dRTC Network and build WebRTC Connections.

# Basic Usage 📝

```python
import asyncio
from ai01.agent import Agent, AgentOptions
from ai01.providers.openai import AudioTrack
from ai01.rtc import RTCOptions, Role, HuddleClientOptions

# Configure RTC options
rtc_options = RTCOptions(
    api_key="your_huddle_api_key",
    project_id="your_project_id",
    room_id="your_room_id",
    role=Role.HOST,
    metadata={"displayName": "AI Agent"}
)

# Initialize Agent
agent = Agent(
    options=AgentOptions(
        rtc_options=rtc_options,
        audio_track=AudioTrack()
    )
)
```

# Module Documentation 📖

The core module can be broken down into the following submodules:

- **`ai01.agent`**: Core module for creating AI agents that can be integrated into WebRTC applications, each agent can be considered as a separate entity that can be connected to a dRTC room, and can interact with other agents and users.

- **`ai01.providers`**: Module for integrating AI providers into the core module, such as OpenAI, Google Cloud, and Microsoft Azure, and also exposes API to integrate custom AI providers.

- **`ai01.rtc`**: Module for integrating Real-Time Communication (RTC) technologies into the core module, such as Huddle, Twilio, and Agora, and also exposes API to integrate custom RTC providers, Each Agent in itself is connected to an RTC room.

Anything can be built with mixing and matching different agents with different models in any pattern which is suitable for the application.

# Agent Module
The Agent module provides the core functionality for creating AI agents that can participate in real-time communication rooms.

An Agent is a high-level entity that can:

- Connect to dRTC network
- Interact with AI models
- Process media streams
- Handle room events

## Agent Methods
- **`join()`**

Join Method is used to join the dRTC Network and establish a websocket connection, upon successful connection the agent is assigned a `room` 
using which agent can setup necessary event listeners before calling `connect` method.

```python
from ai01.agent import Agent, AgentOptions
from ai01.rtc import RoomEvents

room = await agent.join()

@room.on(RoomEvent.RoomJoined)
def on_room_joined():
    print("Room Joined")

```
> Note: The `join` method is an async method and should be awaited before calling any other method.


- **`connect(`)**

Connect Method is used to establish a WebRTC Connection with the room, upon successful connection the agent can start sending and receiving media streams.

```python
await agent.connect()
```

### Events
The Agent module exposes a set of events that can be used to handle room events

```python
from ai01.rtc import RoomEvents, RoomEventsData

@room.on(RoomEvents.NewPeerJoined)
def on_room_joined(data: RoomEventsData.NewPeerJoined):
    print("New Peer Joined the Room",data['remote_peer_id'])
```

The following events are supported:

- `RoomJoined`: Triggered when the agent successfully joins the room, which means the agent is successfully connected to the dRTC network.

- `RoomJoinFailed`: Triggered when the agent fails to join the room, which means the agent is not connected to the dRTC network.

- `RoomClosed`: Triggered when the room is closed, which means the room is no longer available.

- `RoomConnecting`: Triggered when the agent successfully connects to the room, which means the agent is connected to the room.

- `NewPeerJoined`: Triggered when a new peer joins the room, which means a new peer is connected to the room.

- `PeerLeft`: Triggered when a peer leaves the room, which means a peer is disconnected from the room.

- `RemoteProducerAdded`: Triggered when a remote producer is added to the room, which means a remote producer is added to the room.
- `RemoteProducerRemoved`: Triggered when a remote producer is removed from the room, which means a remote producer is removed from the room.

- `NewConsumerAdded`: Triggered when a new consumer is added to the room, which means a new consumer is added to the room.

- `ConsumerClosed`: Triggered when a consumer is closed, which means a consumer is closed.

- `ConsumerPaused`: Triggered when a consumer is paused, which means a consumer is paused.
- `ConsumerResumed`: Triggered when a consumer is resumed, which means a consumer is resumed.


# Providers Module
The Providers module provides a set of APIs for integrating AI providers into the core module.

Currently, the following providers are supported:
- `OpenAI`: 
    1. Realtime API -> ALPHA
    2. Speech-to-Text -> ALPHA
    3. Text-to-Speech -> TODO
- `Gemini`: TODO
- `Anthropic`: TODO
- `grok`: TODO

## OpenAI Provider
The OpenAI provider provides an API for integrating OpenAI models into the core module.

> Note: Currently, the OpenAI Realtime API is only available as provider.
> Issues are open for adding more providers and models, feel free to open a PR or Issue for adding more providers and models.

### Realtime API
Realtime API is a most advanced model by Open_AI which provides direct voice-to-voice communication with the model, which makes it very powerful 
and the response time is the fastest among all the models.

```python
from ai01.providers.openai.realtime import RealTimeModel, RealTimeModelOptions

openai_api_key = os.getenv("OPENAI_API_KEY")


llm = RealTimeModel(
    agent=agent,
    options=RealTimeModelOptions(
        oai_api_key=openai_api_key,
        instructions=bot_prompt,
    ),
)

await llm.connect()
```

This model is still in Beta, but we actively working on it to make it more stable and reliable, and also adding more features to it.

## Methods
**`connect()`**: Connect method is used to establish a connection with the OpenAI Realtime API, upon successful connection the agent can start sending and receiving media streams.

```python
await llm.connect()
```
Upon successful connection, the agent can start sending and receiving media streams, to and from the OpenAI Realtime API.

## Events

Right now the Model pushes all the streams to the `audio_track` of the agent, and the agent can process the audio stream as per the requirement.

# RTC Module

The Core RTC Module is built on-top of the `huddle01` python package, for detailed documentation refer to the documentaion of the `huddle01` package
on [pypi](https://pypi.org/project/huddle01/)


# Contributing 🤝
> This Repository is under active development, and we are actively looking for contributors to help us build this project.

If you are interested in contributing to this project, please refer to the [Contributing Guidelines](https://github.com/Huddle01/huddle01-ai/blob/main/CONTRIBUTING.md).

Keep checking for Latest Issues and PRs, and feel free to open an Issue or PR for any feature or bug.

You can also join the Huddle01 Discord Community for any queries or discussions.

Discord: [Huddle01 Discord](https://discord.gg/huddle01)

# Setting Up the Project Locally 🛠️

To set up the project locally, follow the steps mentioned in the [Setup Guide](https://github.com/Huddle01/huddle01-ai/blob/main/setup.md)

#





