# TamoJunto Crew

Welcome to the TamoJunto Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Installation

Ensure you have Python >=3.10 <3.13 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Customizing

**Add your `OPENAI_API_KEY` into the `.env` file**

- Modify `src/tamo_junto/config/agents.yaml` to define your agents
- Modify `src/tamo_junto/config/tasks.yaml` to define your tasks
- Modify `src/tamo_junto/crew.py` to add your own logic, tools and specific args
- Modify `src/tamo_junto/main.py` to add custom inputs for your agents and tasks

## Running the Project

### Running the Crew from Command Line

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes the tamo_junto Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

### Running the Interactive UI

To launch the interactive web UI for inputting data and viewing the guardian evaluation process:

```bash
$ python -m tamo_junto.run_ui
```

Or use the entry point command if installed via pip:

```bash
$ run_ui
```

The UI allows you to:
1. Input transaction details with the default values from config/inputs.py
2. Add custom JSON inputs as needed
3. View the thinking process of the guardian agents in real-time
4. See the final evaluation outcome and report

## Understanding Your Crew

The tamo_junto Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the TamoJunto Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
