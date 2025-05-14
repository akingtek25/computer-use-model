import argparse
import asyncio
import logging
import sys
import qasync
import os
from dotenv import load_dotenv
import cua
import local_computer
import openai
import vm_computer
import userinterface
from PyQt5.QtWidgets import QApplication


async def agent_loop(agent, window, args, logger):
    logger.info("agent_loop started")
    user_input = await window.get_instructions_async()
    logger.info(f"User: {user_input}")
    agent.start_task()
    while True:
        if not user_input and agent.requires_user_input:
            # Wait for user input from the UI
            user_input = await window.get_user_input_async()
        await agent.continue_task(user_input)
        user_input = None
        if agent.requires_consent and not args.autoplay:
            await window.await_user_ack("Press Enter to run computer tool...")
        elif agent.pending_safety_checks and not args.autoplay:
            await window.await_user_ack(
                f"Safety checks: {agent.pending_safety_checks}\nPress Enter to acknowledge and continue..."
            )
        # Update UI with agent info
        if agent.reasoning_summary:
            window.append_chat(f"Action: {agent.reasoning_summary}")
        for action, action_args in agent.actions:
            window.append_chat(f"  {action} {action_args}")
        if agent.messages:
            window.append_chat(f"Agent: {''.join(agent.messages)}")
        await asyncio.sleep(0.1)  # Yield to event loop


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    # Call your main setup function (not async)
    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--instructions",
        dest="instructions",
        default="Open web browser and go to microsoft.com.",
        help="Instructions to follow",
    )
    parser.add_argument(
        "--model", dest="model", default="tekaisandbox-computer-use-preview"
    )
    parser.add_argument(
        "--endpoint",
        default="azure",
        help="The endpoint to use, either OpenAI or Azure OpenAI",
    )
    parser.add_argument(
        "--autoplay",
        dest="autoplay",
        action="store_true",
        default=True,
        help="Autoplay actions without confirmation",
    )
    parser.add_argument("--environment", dest="environment", default="linux_vm")
    args = parser.parse_args()

    if args.endpoint == "azure":
        client = openai.AsyncAzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version="2025-03-01-preview",
        )
    else:
        client = openai.AsyncOpenAI()

    model = args.model
    computer = local_computer.LocalComputer()
    computer = cua.Scaler(computer, (1024, 768))
    vm = vm_computer.VMComputer(
        hostname=os.getenv("VM_HOSTNAME"),
        username=os.getenv("VM_USERNAME"),
        password=os.getenv("VM_PASSWORD"),
    )
    vm = cua.Scaler(vm, (1024, 768))

    if args.environment == "linux_vm":
        agent = cua.Agent(client, model, vm)
    else:
        agent = cua.Agent(client, model, computer)

    window = userinterface.MainWindow(vm)
    window.show()

    with loop:
        loop.create_task(agent_loop(agent, window, args, logger))
        loop.run_forever()
