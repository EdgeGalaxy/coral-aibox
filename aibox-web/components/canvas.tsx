import React, { useState, useRef, useEffect, memo } from 'react';

type props = {
  url: string
  updateCoordinate: (coordinates: { x: number; y: number }) => void
}


const _Mask = ({ url, updateCoordinate }: props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [ratio, setRatio] = useState<number>(1);
  const height = 480;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    const handleMouseDown = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      drawDot(context, x, y);
      const tx = Math.floor(x / ratio);
      const ty = Math.floor(y / ratio);
      console.log('tx', tx, 'ty', ty, 'x', x, 'y', y)
      updateCoordinate({x: tx, y: ty});
      setIsDrawing(true);
    };

    const handleMouseUp = () => {
      setIsDrawing(false);
    };

    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mouseup', handleMouseUp);

    return () => {
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDrawing, url]);

  useEffect(() => {

    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    const image = new Image();
    image.src = url;
    image.onload = () => {
        // 获取当前组件div的宽高
        const calRatio = height / image.height;
        const canvas_width = height * image.width / image.height;
        // 设置缩放的ratio
        setRatio(calRatio);
        // 设置canvas的宽高
        canvas.width = canvas_width;
        canvas.height = height;
        image.width = canvas_width;
        image.height = height;
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
    }

  }, [url])

  function drawDot(context: CanvasRenderingContext2D, x1: number, y1: number) {
    context.beginPath();
    context.arc(x1, y1, 5, 0, Math.PI * 2);
    context.fillStyle = 'black';
    context.fill();
    context.closePath();
  }

  return (
      <canvas
        ref={canvasRef}
      >
        Your browser does not support the HTML5 canvas tag.
      </canvas>
  );
};

export const Mask = memo(_Mask);