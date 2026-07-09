FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# Install core dependencies, Xvfb, Fluxbox (Window Manager), VNC, and KVM tools
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    xvfb fluxbox wmctrl x11vnc \
    wget unzip \
    openjdk-17-jre cpu-checker qemu-kvm \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

# Set up Android SDK paths
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator

# Install Android Command Line Tools
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip -O /tmp/tools.zip && \
    unzip -q /tmp/tools.zip -d ${ANDROID_HOME}/cmdline-tools && \
    mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest && \
    rm /tmp/tools.zip

# Accept licenses and install emulator image
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-33" "system-images;android-33;google_apis;x86_64" "emulator"

# Create the virtual device
RUN echo "no" | avdmanager create avd -n Pixel_Automation -k "system-images;android-33;google_apis;x86_64"

WORKDIR /app
COPY main.py .
COPY .env .
# Install your Python libraries
RUN pip3 install telebot mss python-dotenv

COPY start.sh .
RUN chmod +x start.sh

# Expose VNC port
EXPOSE 5900

CMD ["./start.sh"]