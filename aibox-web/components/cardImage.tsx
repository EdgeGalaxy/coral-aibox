import { Card, Button, Image } from 'antd';
import { memo, useState } from 'react';
import './cardimage.css'


type Props = {
    imageUrl: string;
    handleDelete: () => void;
};


const _ImageCard = ({ imageUrl, handleDelete }: Props) => {
  const [previewVisible, setPreviewVisible] = useState(false);

  const handlePreview = () => {
    setPreviewVisible(true);
  };


  return (
    <div className="image-card-container">
        <Card className="image-card"
        hoverable
        style={{ width: 240, margin: 10 }}
        cover={<Image alt="example" src={imageUrl} />}
        actions={[
            // <Button onClick={handlePreview}>预览</Button>,
            <Button danger onClick={handleDelete}>删除</Button>
        ]}
        >
        {/* 可以在卡片中添加其他内容或描述 */}
        </Card>

    </div>
  );
};


export const ImageCard = memo(_ImageCard)