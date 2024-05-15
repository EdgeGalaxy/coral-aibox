import React, { memo, useEffect, useState } from 'react';

const showPerson = ( { wsUrl }: { wsUrl: string }) => {
  const [ personCount, setPersonCount ] = useState<number | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Connected to WebSocket");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPersonCount(data.count);
    };

    ws.onclose = () => {
      console.log("Disconnected from WebSocket");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // 组件卸载时关闭WebSocket连接
    return () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    };
  }, []);

  return (
    <div>
        <div className="flex mx-4">
          <p className="mr-4 font-bold text-xl text-center">上报人数: </p> 
          <p className="font-bold text-rose-600 text-xl text-center">{personCount != null ? personCount : '未检测'}</p>
        </div>
    </div>
  );
}


export const ShowPerson = memo(showPerson);