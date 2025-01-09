import asyncio
import json
import logging
import os
from typing import Callable

from dotenv import load_dotenv

from ai01.agent import Agent, AgentOptions, AgentsEvents
from ai01.providers.openai import AudioTrack
from ai01.providers.openai.realtime import (
    RealTimeModel,
    RealTimeModelOptions,
    ServerEvent,
)
from ai01.rtc import (
    HuddleClientOptions,
    ProduceOptions,
    Role,
    RoomEvents,
    RoomEventsData,
    RTCOptions,
)
from example.chatbot.functions.storeAddress import (
    add_complaint,
    add_complaint_tool,
    get_complaint_details,
    get_complaint_details_tool,
)

from .prompt import bot_prompt

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chatbot")


async def main():
    try:
        # Huddle01 API Key
        huddle_api_key = os.getenv("HUDDLE_API_KEY")

        # Huddle01 Project ID
        huddle_project_id = os.getenv("HUDDLE_PROJECT_ID")

        # OpenAI API Key
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not huddle_api_key or not huddle_project_id or not openai_api_key:
            raise ValueError("Required Environment Variables are not set")

        # RTCOptions is the configuration for the RTC
        rtcOptions = RTCOptions(
            api_key=huddle_api_key,
            project_id=huddle_project_id,
            room_id="DAAO",
            role=Role.HOST,
            metadata={"displayName": "Agent"},
            huddle_client_options=HuddleClientOptions(
                autoConsume=True, volatileMessaging=False
            ),
        )

        # Agent is the Peer which is going to connect to the Room
        agent = Agent(
            options=AgentOptions(rtc_options=rtcOptions, audio_track=AudioTrack()),
        )

        # RealTimeModel is the Model which is going to be used by the Agent
        llm = RealTimeModel(
            agent=agent,
            options=RealTimeModelOptions(
                oai_api_key=openai_api_key,
                instructions=bot_prompt,
                function_declaration=[
                    add_complaint_tool,
                    get_complaint_details_tool,
                ],
            ),
        )

        # Join the dRTC Network, which creates a Room instance for the Agent to Join.
        room = await agent.join()

        # Room Events
        @room.on(RoomEvents.RoomJoined)
        def on_room_joined():
            logger.info("Room Joined")

        # @room.on(RoomEvents.NewPeerJoined)
        # def on_new_remote_peer(data: RoomEventsData.NewPeerJoined):
        #     logger.info(f"New Remote Peer: {data['remote_peer']}")

        # @room.on(RoomEvents.RemotePeerLeft)
        # def on_peer_left(data: RoomEventsData.RemotePeerLeft):
        #     logger.info(f"Peer Left: {data['remote_peer_id']}")

        # @room.on(RoomEvents.RoomClosed)
        # def on_room_closed(data: RoomEventsData.RoomClosed):
        #     logger.info("Room Closed")

        # @room.on(RoomEvents.RemoteProducerAdded)
        # def on_remote_producer_added(data: RoomEventsData.RemoteProducerAdded):
        #     logger.info(f"Remote Producer Added: {data['producer_id']}")

        # @room.on(RoomEvents.RemoteProducerClosed)
        # def on_remote_producer_closed(data: RoomEventsData.RemoteProducerClosed):
        #     logger.info(f"Remote Producer Closed: {data['producer_id']}")

        @room.on(RoomEvents.NewConsumerAdded)
        def on_remote_consumer_added(data: RoomEventsData.NewConsumerAdded):
            logger.info(f"Remote Consumer Added: {data}")

            if data["kind"] == "audio":
                track = data["consumer"].track

                if track is None:
                    logger.error("Consumer Track is None, This should never happen.")
                    return

                llm.conversation.add_track(data["consumer_id"], track)

        # @room.on(RoomEvents.ConsumerClosed)
        # def on_remote_consumer_closed(data: RoomEventsData.ConsumerClosed):
        #     logger.info(f"Remote Consumer Closed: {data['consumer_id']}")

        # @room.on(RoomEvents.ConsumerPaused)
        # def on_remote_consumer_paused(data: RoomEventsData.ConsumerPaused):
        #     logger.info(f"Remote Consumer Paused: {data['consumer_id']}")

        # @room.on(RoomEvents.ConsumerResumed)
        # def on_remote_consumer_resumed(data: RoomEventsData.ConsumerResumed):
        #     logger.info(f"Remote Consumer Resumed: {data['consumer_id']}")

        # # Agent Events
        @agent.on(AgentsEvents.Connected)
        def on_agent_connected():
            logger.info("Agent Connected")

        @agent.on(AgentsEvents.Disconnected)
        def on_agent_disconnected():
            logger.info("Agent Disconnected")

        @agent.on(AgentsEvents.Speaking)
        def on_agent_speaking():
            logger.info("Agent Speaking")

        @agent.on(AgentsEvents.Listening)
        def on_agent_listening():
            logger.info("Agent Listening")

        @agent.on(AgentsEvents.Thinking)
        def on_agent_thinking():
            logger.info("Agent Thinking")

        @agent.on(AgentsEvents.ToolCall)
        async def on_tool_call(
            callback: Callable, tool_call: ServerEvent.ResponseFunctionCallArgumentsDone
        ):
            logger.info(f"Tool Call: {tool_call}")
            function_response = {}

            name = tool_call.get("name")
            args = json.loads(tool_call.get("arguments"))

            if name == "add_complaint":
                if not args:
                    print("Missing required parameters 'name' and 'address'")
                argname = args["name"]
                argaddress = args["address"]

                id = add_complaint(argname, argaddress)
                response = "Stored the name and complaint successfully"
                function_response = {
                    "response": response,
                    "complaint_id": id,
                }
            elif name == "get_complaint_details":
                if not args:
                    print("Missing required parameter 'complaint_id'")
                id = args["complaint_id"]

                response = {
                    "error": "Name not found in the complaint book",
                }
                details = get_complaint_details(id)
                if details is not None:
                    response = {
                        "name": details.get("name"),
                        "complaint": details.get("complaint"),
                        "resolution_period": details.get("resolution_period"),
                    }

                function_response = response
            else:
                print(f"Unknown function name: {tool_call.get('name')}")

            await callback(function_response)

        # Connect to the LLM to the Room
        await llm.connect()

        # Connect the Agent to the Room
        await agent.connect()

        if agent.audio_track is not None:
            await agent.rtc.produce(
                options=ProduceOptions(
                    label="audio",
                    track=agent.audio_track,
                )
            )

        # @agent.on(RoomEvents.NewDataMessage)
        # def on_new_data_message(data: AgentEvent.NewDataMessage):
        #     print(f"New Data Message: {data['peer_id']} - {data['message']}")

        # Force the program to run indefinitely
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            logger.info("Exiting...")

    except KeyboardInterrupt:
        print("Exiting...")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
