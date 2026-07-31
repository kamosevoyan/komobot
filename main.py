from src import (
    AppAutomator,
    AppConfig,
    BotController,
    EmulatorController,
    SystemMonitor,
    VisionEngine,
)

if __name__ == "__main__":
    config = AppConfig()
    emulator = EmulatorController(config)
    monitor = SystemMonitor(config, emulator)

    vision = VisionEngine(config)
    automator = AppAutomator(config, emulator, vision)
    bot_controller = BotController(config, automator, monitor, emulator, vision)

    monitor.start()
    bot_controller.start()
