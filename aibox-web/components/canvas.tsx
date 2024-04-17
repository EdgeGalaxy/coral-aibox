import React, { useState, useRef, useEffect, memo } from 'react';

type props = {
  url: string
  updateCoordinate: (coordinates: { x: number; y: number }) => void
}


const _Mask = ({ url, updateCoordinate }: props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);

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
      updateCoordinate({ x, y });
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

    fetch(url).then(response => response.blob()).then((blob) => {
        const image = new Image();
        image.src = URL.createObjectURL(blob);
        image.onload = () => {
            context.drawImage(image, 0, 0, image.width, image.height);
        }
    })
  }, [canvasRef, url])

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