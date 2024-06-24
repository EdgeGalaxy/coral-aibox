'use server';

import * as os from "os";

export type serversMapProps = {
  [key: string]: string
}

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


export async function getAIboxFrpHosts() {
  const frpBaseHost = process.env.FRP_SERVE_HOST
  const frpAuthToken = process.env.FRP_SERVE_AUTH_TOKEN
  const domainSuffix = process.env.DOMAIN_SUFFIX
  // const frpNameSuffix = process.env.frpNameSuffix || "aibox"
  let aiboxServerMapper: serversMapProps = {}
  if (frpBaseHost && domainSuffix && frpAuthToken) {
    const url = `${frpBaseHost}/api/proxy/http`
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Basic ${frpAuthToken}`
      },
    })
    const serverResponse = await fetch(`${frpBaseHost}/api/serverinfo`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Basic ${frpAuthToken}`
      },
    })
    if (response.ok && serverResponse.ok) {
      const serverData = await serverResponse.json()
      const data = await response.json()
      const aiboxServerNames = data.proxies.filter((item: any) => {
        if (item.conf?.type === 'http' && item.conf?.subdomain) {
          return item
        }
      })

      aiboxServerNames.map((item: any) => {
        const host = 'http://' + [item.conf.subdomain, serverData.subdomainHost || domainSuffix].join(".")
        aiboxServerMapper[host] = item.status
      })
      return aiboxServerMapper
    } else {
      console.log("getAIboxFrpHosts error", response.status)
      return aiboxServerMapper
    }
  } else {
    console.log(`ENV get error! frpBaseHost=${frpBaseHost} domainSuffix=${domainSuffix} frpAuthToken=${frpAuthToken}`)
    return aiboxServerMapper
  }
}