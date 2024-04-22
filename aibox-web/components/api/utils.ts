'use server';

import * as os from "os";

export async function getInternalHost() {

  const networkInterfaces = os.networkInterfaces();
  for (const name of Object.keys(networkInterfaces)) {
    for (const net of networkInterfaces[name]) {
      if (net.family === "IPv4" && !net.internal) {
        return `http://${net.address}`;
      }
    }
  }
  return "http://127.0.0.1";
}
