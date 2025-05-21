from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class TamoJunto():
    """TamoJunto crew for evaluating disclosure requests"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def regulatory_body(self) -> Agent:
        return Agent(
            config=self.agents_config['regulatory_body'], # type: ignore[index]
            verbose=True
        )

    @agent
    def major_financial_institution(self) -> Agent:
        return Agent(
            config=self.agents_config['major_financial_institution'], # type: ignore[index]
            verbose=True
        )

    @agent
    def privacy_advocacy_organization(self) -> Agent:
        return Agent(
            config=self.agents_config['privacy_advocacy_organization'], # type: ignore[index]
            verbose=True
        )

    @agent
    def independent_auditor(self) -> Agent:
        return Agent(
            config=self.agents_config['independent_auditor'], # type: ignore[index]
            verbose=True
        )
    
    @agent
    def collation_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['collation_analyst'], # type: ignore[index]
            verbose=True
        )

    @task
    def evaluate_disclosure_regulatory_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_disclosure_regulatory'], # type: ignore[index]
        )

    @task
    def evaluate_disclosure_financial_institution_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_disclosure_financial_institution'], # type: ignore[index]
        )

    @task
    def evaluate_disclosure_privacy_advocacy_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_disclosure_privacy_advocacy'], # type: ignore[index]
        )

    @task
    def evaluate_disclosure_auditor_task(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_disclosure_auditor'], # type: ignore[index]
        )

    @task
    def collation_task(self) -> Task:
        return Task(
            config=self.tasks_config['collation_task'], # type: ignore[index]
            output_file='final_guardian_report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Guardian Evaluation crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
