# AI Agents Coordination & Decision Engine

A multi-agent cybersecurity system that automates cyber threat detection, attack analysis, decision making, incident response, alert generation, and reporting. The project is designed using a modular AI agent architecture where each agent performs a dedicated responsibility and collaborates with other agents to handle security incidents efficiently.



## Overview

Modern organizations generate a large volume of security logs every day. Analyzing these logs manually can delay incident detection and response.

This project introduces a coordinated AI agent framework that processes security events through multiple independent agents. Each agent performs a specific task and passes its output to the next agent, creating an automated cyber incident response workflow.



## Objectives

- Detect suspicious cyber activities from security logs.
- Analyze detected events to identify attack types.
- Evaluate attack severity.
- Recommend appropriate response actions.
- Generate security alerts.
- Prepare incident reports automatically.





## AI Agents

### Detection Agent
Monitors incoming cyber logs and identifies suspicious activities based on predefined security rules.

### Analysis Agent
Analyzes suspicious events, classifies attack types, and assigns severity levels.

### Decision Agent
Determines the most suitable response based on the analyzed threat.

### Response Agent
Executes the recommended mitigation strategy.

### Alert Agent
Generates alerts for administrators with relevant incident details.

### Report Agent
Creates a structured incident report summarizing the complete response process.


## Technologies

- Python
- Pandas
- OpenPyXL
- LangChain
- LangGraph
- Streamlit
- Git & GitHub



## Project Structure


AI-Agents-Coordination-Decision-Engine/
│
├── agents/
│   ├── detection_agent.py
│   ├── analysis_agent.py
│   ├── decision_agent.py
│   ├── response_agent.py
│   ├── alert_agent.py
│   └── report_agent.py
│
├── prompts/
│
├── data/
│
├── main.py
├── requirements.txt
└── README.md




## Current Progress

### Completed

- Project initialization
- Repository setup
- Environment configuration
- Detection Agent
- AI agent framework
- Prompt templates
- Sample cyber log dataset

### In Progress

- Analysis Agent
- Decision Agent
- Response Agent
- Alert Agent
- Report Generation
- Streamlit Dashboard

---

## Future Enhancements

- LLM-powered decision support
- Real-time cyber log monitoring
- Automated alert notifications
- Interactive Streamlit dashboard
- Cloud deployment
- Performance optimization

---

## Author

**Madhumitha V**

B.Tech Information Technology

Nehru Institute of Engineering and Technology