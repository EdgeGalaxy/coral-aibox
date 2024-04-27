import { Modal } from "antd"
import { memo } from "react"


const _activeModal = ({ isOpen }: { isOpen: boolean }) => {
    return (
        <Modal open={isOpen} closable={false} footer={null}>
            <p className="font-bold text-red-600 text-2xl">您的服务未激活，请去服务器上设置激活码后然后重启服务！！！！</p>
        </Modal>

    )
}


export const ActiveModal = memo(_activeModal)