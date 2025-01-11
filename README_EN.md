# VRChat Haptic Feedback System

[中文](./README.md)

Experience realistic haptic feedback through VRChat touch interactions.

## Features

- Support haptic feedback triggered by touching specific Avatar areas
- Support multiple Coyote devices for multiplayer interaction
- Fully compatible with MA prefabs
- Customizable trigger zones

## Requirements

- Coyote 3.0 Device
- VRChat Account
- MA-compatible Avatar
- Python 3.8 or higher
- WebSocket support

## Software Installation

1. Clone the repository:
```bash
git clone https://github.com/你的用户名/项目名.git
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the program:
```bash
python main.py
```

## Avatar Setup

1. Download the latest version of the prefab
2. Import the prefab into your Avatar project
3. Place trigger components at desired haptic feedback locations
4. Ensure all variable names match the prefab

## Usage

1. Launch VRChat and enter the game
2. Connect Coyote device to WebSocket
3. Press the circular button on device channel A to start receiving signals
4. When other players touch the trigger zones, corresponding haptic feedback will be generated

## Notes

- Current version is still under development and may have known issues
- Please check device connection status before use
- Submit an Issue if you encounter any problems

## Contributing

Pull Requests and Issues are welcome to help improve the project.

## License

[License Type]