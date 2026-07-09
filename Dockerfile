FROM ubuntu:22.04

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies, Xvfb, wmctrl, and KVM tools
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    xvfb wmctrl \
    wget unzip \
    openjdk-17-jre cpu-checker qemu-kvm \
    && rm -rf /var/lib/apt/lists/*

# Set up the Android SDK environment variables
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator

# Download and install Android Command Line Tools
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip -O /tmp/tools.zip && \
    unzip -q /tmp/tools.zip -d ${ANDROID_HOME}/cmdline-tools && \
    mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest && \
    rm /tmp/tools.zip

# Accept licenses and install the system image (x86_64 with Google APIs)
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-33" "system-images;android-33;google_apis;x86_64" "emulator"

# Create the virtual device
RUN echo "no" | avdmanager create avd -n Pixel_Automation -k "system-images;android-33;google_apis;x86_64"

# Copy your Python bot script and requirements
WORKDIR /app
COPY main.py .
COPY .env .
RUN pip3 install telebot mss python-dotenv

# Create a startup script
COPY start.sh .
RUN chmod +x start.sh

# Run the startup script
# CMD ["./start.sh"]
CMD ["sleep", "infinity"]
