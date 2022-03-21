# ==== High DPI support on Windows ====
# To enable DPI awareness on Windows you have to either embed DPI aware manifest
# in your executable created with pyinstaller or change python.exe properties manually:
# Compatibility > High DPI scaling override > Application.
# Setting DPI awareness programmatically via a call to cef.DpiAware.EnableHighDpiSupport
# is problematic in Python, may not work and can cause display glitches.

from cefpython3 import cefpython as cef
import sys
import os
from app_session import CustomAppSession
from streamlit.script_runner import ScriptRunnerEvent
from streamlit.session_data import SessionData
from streamlit.uploaded_file_manager import UploadedFileManager
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ClientHandler:

    # RequestHandler.GetResourceHandler()
    def GetResourceHandler(self, browser, frame, request):
        # Called on the IO thread before a resource is loaded.
        # To allow the resource to load normally return None.
        resHandler = ResourceHandler()
        resHandler._clientHandler = self
        resHandler._browser = browser
        resHandler._frame = frame
        resHandler._request = request
        self._AddStrongReference(resHandler)
        return resHandler

    def _OnResourceResponse(self, browser, frame, request, requestStatus,
            requestError, response, data):
        return data

    # A strong reference to ResourceHandler must be kept
    # during the request. Some helper functions for that.
    # 1. Add reference in GetResourceHandler()
    # 2. Release reference in ResourceHandler.ReadResponse()
    #    after request is completed.

    _resourceHandlers = {}
    _resourceHandlerMaxId = 0

    def _AddStrongReference(self, resHandler):
        self._resourceHandlerMaxId += 1
        resHandler._resourceHandlerId = self._resourceHandlerMaxId
        self._resourceHandlers[resHandler._resourceHandlerId] = resHandler

    def _ReleaseStrongReference(self, resHandler):
        if resHandler._resourceHandlerId in self._resourceHandlers:
            del self._resourceHandlers[resHandler._resourceHandlerId]
        else:
            print("_ReleaseStrongReference() FAILED: resource handler " \
                    "not found, id = %s" % (resHandler._resourceHandlerId))

class ResourceHandler:

    # The methods of this class will always be called
    # on the IO thread.

    _resourceHandlerId = None
    _clientHandler = None
    _browser = None
    _frame = None
    _request = None
    _callback = None
    _webRequest = None
    _webRequestClient = None
    _offsetRead = 0
    _data = None
    _mime = None

    def ProcessRequest(self, request, callback):
        self._callback = callback
        url = request.GetUrl()

        #Only handle file:// requests
        if not url.startswith("file://"):
            return False

        #Remove 'file://' and any trailing slash
        url = url[7:]
        if url[-1] == '/':
            url = url[:-1]

        #If blank, default to index.html
        if url == "":
            url = "index.html"

        f = open(resource_path(url), 'rb')
        self._data = f.read()
        f.close()

        #If it is index.html, insert the websocket shim
        if url.endswith("index.html"):
            with open(resource_path(os.path.join("frontend", "websocketshim.js")), "r") as f:
                self._data = str(self._data).replace("<head>", "<head><script>" + f.read() + "</script>", 1).encode()

        if url.endswith('.html'):
            self._mime = "text/html"
        if url.endswith('.js'):
            self._mime = "text/javascript"
        if url.endswith('.css'):
            self._mime = "text/css"
        if url.endswith('.ttf'):
            self._mime = "font/ttf"
        if url.endswith('.woff'):
            self._mime = "font/woff"
        if url.endswith('.woff2'):
            self._mime = "font/woff2"
        if url.endswith('.js.map'):
            self._mime = "application/json"

        self._callback.Continue()
        return True

    def GetResponseHeaders(self, response, responseLengthOut, redirectUrlOut):
        response.SetStatus(200)
        response.SetStatusText("ok")
        response.SetMimeType(self._mime)
        responseLengthOut[0] = len(self._data)

    def ReadResponse(self, data_out, bytes_to_read, bytes_read_out, callback):
        # 1. If data is available immediately copy up to
        #    bytesToRead bytes into dataOut[0], set
        #    bytesReadOut[0] to the number of bytes copied,
        #    and return true.
        # 2. To read the data at a later time set
        #    bytesReadOut[0] to 0, return true and call
        #    callback.Continue() when the data is available.
        # 3. To indicate response completion return false.
        if self._offsetRead < len(self._data):
            dataChunk = self._data[self._offsetRead:(self._offsetRead + bytes_to_read)]
            self._offsetRead += len(dataChunk)
            data_out[0] = dataChunk
            bytes_read_out[0] = len(dataChunk)
            return True
        self._clientHandler._ReleaseStrongReference(self)
        return False

    def CanGetCookie(self, cookie):
        # Return true if the specified cookie can be sent
        # with the request or false otherwise. If false
        # is returned for any cookie then no cookies will
        # be sent with the request.
        return True

    def CanSetCookie(self, cookie):
        # Return true if the specified cookie returned
        # with the response can be set or false otherwise.
        return True

    def Cancel(self):
        # Request processing has been canceled.
        pass

def main():
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    cef.Initialize()

    browser = cef.CreateBrowserSync(window_title="Hello World!")

    bindings  = cef.JavascriptBindings()

    session = None
    def py_connect(send_msg):
        nonlocal session
        def handle_message():
            messages = session.flush_browser_queue()
            for msg in messages:
                m = msg.SerializeToString().hex()
                send_msg.Call(m)

        session = CustomAppSession(
            SessionData("", ""),
            UploadedFileManager(),
            handle_message
        )

        session._on_scriptrunner_event(ScriptRunnerEvent.SCRIPT_STARTED)
        print("Connected")
        session.request_rerun(None)

    def on_message(message):
        nonlocal session
        msg = BackMsg()
    
        msg.ParseFromString(bytes.fromhex(message))
        msg_type = msg.WhichOneof("type")
        if msg_type == "rerun_script":
            session.handle_rerun_script_request(msg.rerun_script)
        elif msg_type == "load_git_info":
            session.handle_git_information_request()
        elif msg_type == "clear_cache":
            session.handle_clear_cache_request()
        elif msg_type == "set_run_on_save":
            session.handle_set_run_on_save_request(msg.set_run_on_save)
        elif msg_type == "stop_script":
            session.handle_stop_script_request()
        else:
            print('No handler for "%s"', msg_type)

    bindings.SetFunction("py_connect", py_connect)
    bindings.SetFunction("py_send_msg", on_message)
    browser.SetJavascriptBindings(bindings)
    browser.SetClientHandler(ClientHandler())

    browser.LoadUrl("file://frontend/index.html")

    cef.MessageLoop()
    cef.Shutdown()

if __name__ == '__main__':
    main()