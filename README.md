# PulseSearch

PulseSearch is a Python-based software program designed for optimizing and running THz time-domain spectroscopy measurements. It provides a user-friendly interface for controlling instruments, running measurements, and optimizing/alignment.

## Features
- **Optimization Interface**: Easily configure and optimize pulse sequences.
- **Instrument Control**: Seamless communication with experimental instruments.
- **Measurement Execution**: Automate and manage experimental measurements.
- **Modular Design**: Clear separation of functionality across different modules. Intended to be structured as Machine-Controller-Viewer.

## Installation

To get started with PulseSearch, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/Pulsesearch.git
    cd Pulsesearch
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

    The main dependencies include:
    - **PyQt5**: For building the graphical user interface.
    - **NumPy**: For numerical computations.
    - **SciPy**: For optimization routines.
    - **PyVisa**: For instrument communication.

3. Ensure that all required instruments are connected and properly configured.

## Usage

The program is modular, with several main files primarily organized through `pulseSearch.py`.

### Launching the Program
To start the PulseSearch application, use the `programManager.py` script:
```bash
python programManager.py
```

This script serves as the main entry point for the application.

### Optimization Interface
The `pulseSearch.py` script manages the optimization interface, allowing users to configure the instruments, engage in fine manual control of all instruments, and optimize (hopefully) with ease. This also handles the main interface, safety measured for the intake of data, and will launch the other mode of the software such as scanning, quicksaves, or quickFFTs:
```bash
python pulseSearch.py
```

### Running Measurements
The `scanProgV4p0.py` script is used to execute measurements. It handles the experimental data acquisition process:
```bash
python scanProgV4p0.py
```

### Instrument Communication
The `instrumentControl.py` script manages the direct communication with the instruments. It ensures seamless integration between the software and hardware. These classes will be setup depending on what is connected, and interfaced with primarily using some level of organization and abstraction from the motionController class:
```bash
python instrumentControl.py
```

## Contributing

Honestly I love this program, and it has made data acquisition so much kinder than previous labVIEW programs we were stuck on. This framework should be easily adjusted to work for many other types of optical measurements, whether it be equilibrium or nonequilibrium, THz or optical probe. For anyone who is interested in adapting this for their use or intending to design something similar, please let me know if I can help at all. -warsh

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

Special thanks to the contributors and the open-source community for their support in making this project possible.
