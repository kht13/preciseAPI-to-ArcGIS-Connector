# PreciseAPI to ArcGIS Connector

This python application is for reading real-time geospatial data from [PreCise](https://precisemrm.com/) and displaying the data on an [ArcGIS](https://arcgis.com/) layer. As long as the app is turned on with correct credentials for both PreCise and ArcGIS, it will periodically pull data from PreCise and update the layer.

This app uses Python 3.14 with `arcgis`, `requests` and `PySide6` libraries. The documentation for the Precise API used in this app can be found [here](https://api-myfleet.precisemrm.com/help).

## Downloading and Installing

Currently, only the Windows version of the built app is available. The app has been built to not require any additional downloads or installations. You can run it by downloading the zip file, extracting it, and running the `app.exe` file inside. The built version can be downloaded from [Releases](https://github.com/kht13/preciseAPI-to-ArcGIS-Connector/releases/latest).

If you want to run the app on other operating systems, refer to the [Running the Source Code](#running-the-source-code) section.

## Running the Source Code

If you want to download the source code and run it or build the app yourself, you can follow the directions below:

#### Clone the project

```bash
  git clone https://github.com/kht13/preciseAPI-to-ArcGIS-Connector
```

#### Go to the project directory

```bash
  cd preciseAPI-to-ArcGIS-Connector
```

#### Install dependencies

```bash
  py -m pip install -r requirements.txt
```

#### Run the app

```bash
  py app.py
```

*The exact commands might be different depending on the Python configurations.*

## Building the App Locally

The app version 0.1.1 in the Releases section was built for Windows using `nuitka`. Below is the command used:

```bash
  py -m nuitka app.py --standalone --windows-console-mode=attach --enable-plugin=pyside6 --msvc=latest --include-package-data=puremagic --include-package=arcgis.gis --include-data-files="./icons/*.svg"=icons/ --include-data-files="./layerDefinitions/*.json"=layerDefinitions/
```

The `--msvc=latest` flag requires Visual Studio 2022 (or higher) and the C++ package for it. On different operating systems, `gcc` or `clang` might be better choices. For more information, please refer to [this guide](https://nuitka.net/user-documentation/user-manual.html#id18). 

