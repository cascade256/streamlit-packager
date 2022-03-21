# Streamlit Packager

This is a tool that can take an un-modified [Streamlit](https://github.com/streamlit/streamlit) script and package it into an executable that can be run offline and without a server. Some use cases where this might be useful:

- Deploying to users with a strictly filtered or unreliable internet connection.
- When working with sensitive data.

## How to use

For reference, assume you have a folder structure like this:
```
- MyAwesomeProject/
    - MyAwesomeScript.py
```

Clone this repository:

``` bash
git clone https://github.com/cascade256/StreamlitPackager
```

This should give you a folder structure like this:
```
- MyAwesomeProject/
    - MyAwesomeScript.py
    - StreamlitPackager/
        - run.sh
        - package.py
        ...
```

To keep the size of the final package down, it is strongly recommended to create a Python environment with only the needed packages and run the packaging commands from inside that environment. PyInstaller can be pretty agressive about including packages that are not truly needed and can cause the package size to become very large.

To build the package, run this command:
``` bash
StreamlitPackager/run.sh MyAwesomeScript.py
```

Once that finishes, there should be a file called `MyAwesomeApp` in you project folder. That is your packaged program! 

To customize how it is packaged, take a look at `run.sh`. It serves as a nice starting point for configuring the options.

## How it works - Basic

Instead of running a server that your browser will request to run and get the script results, the browser and server are merged into a single program. The "browser" in this case is Chromium Embedded Framework, a flavor of Google Chrome.

## How it works - Advanced

The script that actually runs is `main.py`, which uses CEFPython to open a window. A resource handler is set up to intercept requests and return the front end files from the installed Streamlit package. The frontend normally uses a WebSocket to communicate with the server, but CEF doesn't have a method to intercept WebSockets. So when `index.html` is loaded, a shim (`websocketshim.js`) is inserted that overwrites the WebSocket class and sets up communication over Python/JS bindings. The messages between the frontend and server are normally binary encoded, but as far as I could find, CEFPython only allows strings. So the Python and JS message handlers encode and decode from hex.  

Once communication is established, the frontend will request the Streamlit script to be run. To do this, `main.py` uses `app_session.py` to handle the session, which in turn uses `script_runner.py` to run the script. `app_session.py` and `script_runner.py` are both lightly modified files from the Streamlit project and import many other unmodified Streamlit files. `script_runner.py` runs the function `__streamlit_run__` in the `built_streamlit_script.py` file.

That file is generated from the specified Streamlit script with these steps:

1. The script is run through the Streamlit magic processor: https://docs.streamlit.io/library/api-reference/write-magic/magic
1. The contents of the script are placed into a function `__streamlit_run__()`
1. Any imports are hoisted to the top of the file, outside of `__streamlit_run__()`
1. It is output to `built_streamlit_script.py`

There are two reasons for doing this instead of just letting `script_runner.py` run it normally. The first is for the packaging step. By having an import chain from `main.py` to the script, it and its dependencies will be automatically included in the package. The second is to save some time re-loading the script each time it is run.

For the actual packaging, PyInstaller does the vast majority of the work. `package.py` is a simple wrapper around pyinstaller that builds `built_streamlit_script.py`, handles finding and adding the frontend files, and setting up the hooks in `hooks/`. The main hook is for CEFPython, which is adapted from a CEFPython example. The other is for the `altair` package, which has been added to the PyInstaller hooks repository, but may not be available depending on the release.

## Known issues

- The executables are quite large, with a basic app package as a single file, compressed app being ~175 MB. The same app packaged as a mutlitple file, uncompressed app is ~475 MB. The largest parts are:

    - cefpython3: ~190 MB
    - streamlit frontend: ~98 MB
    - pyarrow: ~60 MB

- Streamlit config options are not supported yet
- Uploading files is not supported yet