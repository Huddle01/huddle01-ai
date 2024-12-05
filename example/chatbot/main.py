import asyncio
import logging
import os

from dotenv import load_dotenv

from ai01.agent import Agent, AgentEventsData, AgentOptions, AgentsEvents
from ai01.providers.openai import AudioTrack
from ai01.providers.openai.realtime import RealTimeModel, RealTimeModelOptions
from ai01.rtc import HuddleClientOptions, Role, RoomEvents, RoomEventsData, RTCOptions

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
            ),
        )

        # Join the dRTC Network, which creates a Room instance for the Agent to Join.
        room = await agent.join()

        # Room Events
        @room.on(RoomEvents.RoomJoined)
        def on_room_joined(data: RoomEventsData.RoomJoined):
            print("Room Joined")

        @room.on(RoomEvents.NewPeerJoined)
        def on_new_remote_peer(data: RoomEventsData.NewPeerJoined):
            logger.info(f"New Remote Peer: {data['remote_peer']}")

        @room.on(RoomEvents.RemotePeerLeft)
        def on_peer_left(data: RoomEventsData.RemotePeerLeft):
            logger.info(f"Peer Left: {data['remote_peer_id']}")

        @room.on(RoomEvents.RoomClosed)
        def on_room_closed(data: RoomEventsData.RoomClosed):
            logger.info("Room Closed")

        @room.on(RoomEvents.RemoteProducerAdded)
        def on_remote_producer_added(data: RoomEventsData.RemoteProducerAdded):
            logger.info(f"Remote Producer Added: {data['producer_id']}")

        @room.on(RoomEvents.RemoteProducerClosed)
        def on_remote_producer_closed(data: RoomEventsData.RemoteProducerClosed):
            logger.info(f"Remote Producer Closed: {data['producer_id']}")

        @room.on(RoomEvents.NewConsumerAdded)
        def on_remote_consumer_added(data: RoomEventsData.NewConsumerAdded):
            logger.info(f"Remote Consumer Added: {data['consumer_id']}")

        @room.on(RoomEvents.ConsumerClosed)
        def on_remote_consumer_closed(data: RoomEventsData.ConsumerClosed):
            logger.info(f"Remote Consumer Closed: {data['consumer_id']}")

        @room.on(RoomEvents.ConsumerPaused)
        def on_remote_consumer_paused(data: RoomEventsData.ConsumerPaused):
            logger.info(f"Remote Consumer Paused: {data['consumer_id']}")

        @room.on(RoomEvents.ConsumerResumed)
        def on_remote_consumer_resumed(data: RoomEventsData.ConsumerResumed):
            logger.info(f"Remote Consumer Resumed: {data['consumer_id']}")


        # Agent Events
        @agent.on(AgentsEvents.AgentConnected)
        def on_agent_connected(data: AgentEventsData.Connected):
            logger.info(f"Agent Connected: {data['peer_id']}")

        @agent.on(AgentsEvents.AgentDisconnected)
        def on_agent_disconnected(data: AgentEventsData.Disconnected):
            logger.info(f"Agent Disconnected: {data['peer_id']}")

        @agent.on(AgentsEvents.AgentSpeaking)
        def on_agent_speaking(data: AgentEventsData.Speaking):
            logger.info(f"Agent Speaking: {data['peer_id']}")

        @agent.on(AgentsEvents.AgentListening)
        def on_agent_listening(data: AgentEventsData.Listening):
            logger.info(f"Agent Listening: {data['peer_id']}")

        @agent.on(AgentsEvents.AgentThinking)
        def on_agent_thinking(data: AgentEventsData.Thinking):
            logger.info(f"Agent Thinking: {data['peer_id']}")


        # Connect to the LLM to the Room
        await llm.connect()

        # Connect the Agent to the Room
        await agent.connect()

        # @agent.on(RoomEvents.NewDataMessage)
        # def on_new_data_message(data: AgentEvent.NewDataMessage):
        #     print(f"New Data Message: {data['peer_id']} - {data['message']}")

        # Force the program to run indefinitely
        await asyncio.Future()
    except KeyboardInterrupt:
        print("Exiting...")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
