import React, { memo, useState } from "react";
import { Button, Modal, Form, Input, message } from "antd";


type FormValues = {
  baseUrl: string;
};


const _baseUrlCard = ({ isVisible, baseUrl }: { isVisible: boolean, baseUrl: string }) => {

  const [ visible, setVisible] = useState(isVisible);
  const [form] = Form.useForm<FormValues>();

  const showModal = () => {
    setVisible(true);
  };

  const handleSubmit = () => {
    form
      .validateFields()
      .then((values: FormValues) => {
        let url = values['baseUrl'];
        if (url.endsWith("/")) {
          url = url.slice(0, -1);
        }
        // 通过请求cameras接口判断url是否可用
        fetch(`${baseUrl}/api/aibox_camera/cameras`)
          .then((response) => response.json())
          .then((cameras) => {
            window.localStorage.setItem("frpHost", url);
            message.success("切换成功");
            setVisible(false);
            window.location.reload()
          }).catch((error) => {
            message.error("切换失败: [ url请求未通过 ]");
          });
      }).catch((error) => {
        message.error("切换失败: " + error);
      })
  };

  const handleCancel = () => {
    setVisible(false);
  };

  return (
    <div>
      <Button type="primary" onClick={showModal}>
        切换域名
      </Button>
      <Modal
        title="域名切换"
        keyboard={false}
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText="切换"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" name="form_in_modal">
          <Form.Item
            name="baseUrl"
            label="域名地址"
            initialValue={baseUrl}
            rules={[{ required: true, message: "请输入对应的域名地址" }, { type: 'url', message: "请输入正确的域名, http开头" }]}
          >
            <Input defaultValue={ baseUrl }/>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export const BaseUrlCard = memo(_baseUrlCard);
