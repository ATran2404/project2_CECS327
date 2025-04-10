# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask==3.0.2 uuid==1.30 requests==2.31.0

# Copy the application
COPY node.py .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "node.py"] 