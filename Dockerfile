# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the Python script into the container at /usr/src/app
COPY get-specs-data.py .

# Install the necessary Python packages
RUN pip install --no-cache-dir jira

# Define environment variable
ENV JIRA_TOKEN=""

# Run the application
CMD ["python", "./get-specs-data.py"]