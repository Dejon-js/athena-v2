# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Add the working directory to the PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip -r /app/requirements.txt

# Copy the rest of the backend application code into the container at /app
COPY . /app

# Command to run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]