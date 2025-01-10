import asyncio
import logging
import os
from typing import Callable

from dotenv import load_dotenv
from google.genai import types

from ai01.agent import Agent, AgentOptions, AgentsEvents
from ai01.providers.gemini.gemini_realtime import (
    GeminiConfig,
    GeminiOptions,
    GeminiRealtime,
)
from ai01.providers.openai import AudioTrack
from ai01.rtc import (
    HuddleClientOptions,
    ProduceOptions,
    Role,
    RoomEvents,
    RoomEventsData,
    RTCOptions,
)
from example.gemini.functions.storeAddress import (
    add_complaint,
    add_complaint_tool,
    check_for_complaint,
    check_for_complaint_tool,
    get_complaint_details,
    get_complaint_details_tool,
)

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chatbot")


async def main():
    try:
        # Huddle01 API Key
        huddle_api_key = os.getenv("HUDDLE_API_KEY")

        # Huddle01 Project ID
        huddle_project_id = os.getenv("HUDDLE_PROJECT_ID")

        # gemini API Key
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not huddle_api_key or not huddle_project_id or not gemini_api_key:
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
        llm = GeminiRealtime(
            agent=agent,
            options=GeminiOptions(
                gemini_api_key=gemini_api_key,
                system_instruction="""### Role
                You are an AI Customer Support Agent named Sophie, Your role is to register customer complaints.
                There are three things the customer can do:
                    1. Register a complaint: if they want to register a complaint. ask for their name and complaint.
                    2. Check for a complaint: if they want to check if their complaint is already registered. ask for their name.
                    3. Get complaint details: if they want to get the details of their complaint. ask for their name.""",
                config=GeminiConfig(
                    function_declaration=[
                        add_complaint_tool,
                        check_for_complaint_tool,
                        get_complaint_details_tool,
                    ],
                ),
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
        async def on_tool_call(callback: Callable, tool_call: types.LiveServerToolCall):
            logger.info(f"Tool Call: {tool_call}")
            function_responses = []

            if tool_call.function_calls:
                for function_call in tool_call.function_calls:
                    name = function_call.name
                    args = function_call.args
                    # Extract the numeric part from Gemini's function call ID
                    call_id = function_call.id
                    if name == "check_for_complaint":
                        if not args:
                            print("Missing required parameter 'name'")
                            continue
                        argname = args["name"]
                        boolean = check_for_complaint(argname)
                        function_responses.append(
                            {
                                "name": "check_for_complaint",
                                "response": {"exists": boolean},
                                "id": call_id,
                            }
                        )
                    elif name == "add_complaint":
                        if not args:
                            print("Missing required parameters 'name' and 'complaint'")
                            continue
                        argname = args["name"]
                        argcomplaint = args["complaint"]

                        add_complaint(argname, argcomplaint)
                        response = (
                            f"Stored the complaint of {argname} as {argcomplaint}"
                        )
                        function_responses.append(
                            {
                                "name": "add_complaint",
                                "response": {"response": response},
                                "id": call_id,
                            }
                        )
                    elif name == "get_complaint_details":
                        if not args:
                            print("Missing required parameter 'name'")
                            continue
                        argname = args["name"]

                        response = {
                            "error": "Name not found in the complaint book",
                        }

                        details = get_complaint_details(argname)

                        if details is not None:
                            response = {
                                "complaint": details.get("complaint"),
                                "resolution_period": details.get("resolution_period"),
                            }

                        function_responses.append(
                            {
                                "name": "get_complaint_details",
                                "response": response,
                                "id": call_id,
                            }
                        )
                    else:
                        print(f"Unknown function name: {function_call.name}")

            await callback(function_responses)

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
