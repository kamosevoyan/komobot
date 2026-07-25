FROM ubuntu:22.04

ARG ANDROID_SKD_VERSION=28

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

# Accept licenses and install the PLAY STORE emulator image
RUN yes | sdkmanager --licenses && \
    sdkmanager "platform-tools" "platforms;android-${ANDROID_SKD_VERSION}" "system-images;android-${ANDROID_SKD_VERSION};google_apis_playstore;x86_64" "emulator"

# Create the virtual device
RUN echo "no" | avdmanager create avd -n Pixel_Automation -k "system-images;android-${ANDROID_SKD_VERSION};google_apis_playstore;x86_64"
RUN echo "hw.keyboard=yes" >> /root/.android/avd/Pixel_Automation.avd/config.ini

WORKDIR /app
COPY main.py .
COPY requirements.txt .

# Install Python libraries
RUN pip3 install -r requirements.txt

COPY start.sh .
RUN chmod +x start.sh

# Expose VNC port
EXPOSE 5900

CMD ["./start.sh"]