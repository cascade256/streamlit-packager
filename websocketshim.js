
(() => {
    function hexToBytes(hex) {
        const buffer = new ArrayBuffer(hex.length / 2);
        const bytes = new Uint8Array(buffer);
        for (let c = 0; c < hex.length; c += 2)
            bytes[c / 2] = parseInt(hex.substr(c, 2), 16);
        return bytes;
    }

    const byteToHex = [];

    for (let n = 0; n <= 0xff; ++n)
    {
        const hexOctet = n.toString(16).padStart(2, "0");
        byteToHex.push(hexOctet);
    }
    function bytesToHex(arrayBuffer)
    {
        const buff = new Uint8Array(arrayBuffer);
        const hexOctets = new Array(buff.length);

        for (let i = 0; i < buff.length; ++i)
            hexOctets[i] = byteToHex[buff[i]];

        return hexOctets.join("");
    }

    class WebSocketShim {

        constructor(url) {
            window.socket = this;
            setTimeout(() => {
                py_connect((msg) => {

                    let bytes = hexToBytes(msg);
                    // console.log(bytes);
                    this.onmessage({data: bytes});
                })
                this.readyState = 1;
                this.onopen();
            }, 20);
        }

        send(message) {
            let hex = bytesToHex(message); 
            py_send_msg(hex)
        }

        close() {

        }
    }
    window.WebSocket = WebSocketShim;
})();