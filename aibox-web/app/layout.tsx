"use client";

import "./globals.css";
import { usePathname } from 'next/navigation';

import { Inter } from "next/font/google";
import Link from "next/link";

import { ActiveModal } from "@/components/activeModel";

import {
  DesktopOutlined,
  RedoOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  MessageOutlined,
  BlockOutlined,
  
} from "@ant-design/icons";
import { Layout, Menu, theme } from "antd";
import {  useEffect, useLayoutEffect, useState } from "react";
import { BaseUrlCard } from "@/components/baseUrlCard";
import { GlobalContext } from "@/components/api/context";

const { Header, Content, Footer, Sider } = Layout;

const inter = Inter({ subsets: ["latin"] });

const menuItems = [
  {
    label: "显示",
    key: "/",
    url: "/",
    icon: <DesktopOutlined />,
  },
  {
    label: "Mask配置",
    key: "/mask",
    url: "/mask",
    icon: <BlockOutlined />,
  },
  {
    label: "预加载",
    key: "/preload",
    url: "/preload",
    icon: <RedoOutlined />,
    children: [
      {
        label: "人物误检",
        key: "/preload/person",
        url: "/preload/person",
        icon: <TeamOutlined />,
      },
      // {
      //   label: "面部识别",
      //   key: "/preload/face",
      //   url: "/preload/face",
      //   icon: <IdcardOutlined />,
      // }
    ]
  },
  {
    label: "录像",
    key: "/record",
    url: "/record",
    icon: <VideoCameraOutlined />,
  },
  {
    label: "事件",
    key: "/event",
    url: "/event",
    icon: <MessageOutlined />,
  },
  // {
  //   label: "升级",
  //   key: "/upgrade",
  //   url: "/upgrade",
  //   icon: <UpOutlined />,
  // },
];



export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [ isLoading, setIsLoading ] = useState<boolean>(true);
  const [ baseUrl, setBaseUrl] = useState<string>("");
  const [ collapsed, setCollapsed ] = useState<boolean>(false);
  const [ visible, setVisible ] = useState<boolean>(false);
  const {
    token: { colorBgContainer },
  } = theme.useToken();
  const [ isActived, setIsActived ] = useState<boolean>(true);

  // 获取当前路径
  const currentPath = usePathname()

  useLayoutEffect(() => {
    setIsLoading(true);
    if (typeof window !== "undefined" && window.localStorage) {
        const _baseUrl = window.localStorage.getItem("frpHost") || "";
        setBaseUrl(_baseUrl);
        if (!_baseUrl) {
          setVisible(true);
        }
    } else {
      setVisible(true);
    }
    setIsLoading(false);
  }, [])

  useEffect(() => {
    if (baseUrl === "") {
      return;
    }
    fetch(`${baseUrl}/api/aibox_camera/cameras/is_actived`)
      .then((response) => response.json())
      .then((isActived) => setIsActived(isActived));

    if (currentPath != "/") {
      fetch(`${baseUrl}/api/aibox_camera/cameras/stop_stream`)
        .then((response) => response.json())
        .then((data) => {
          console.log('origin camera data', data)
        })
      
      fetch(`${baseUrl}/api/aibox_face/cameras/stop_stream`)
        .then((response) => response.json())
        .then((data) => {
          console.log('inference camera data', data)
        })
    }
  }, [baseUrl, currentPath])

  // 确定哪个菜单项应该高亮
  const selectedKeys = menuItems
    .filter(item => currentPath === item.key)
    .map(item => item.key);
  
  // if (isLoading) {
  //   return <div>Loading...</div>;
  // }

  return (
    <html lang="en">
      <body className={inter.className}>
        <Layout style={{ minHeight: "100vh" }}>
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={(value) => setCollapsed(value)}
          >
            <div className="demo-logo-vertical m-12" />
            <Menu
              theme="dark"
              defaultSelectedKeys={selectedKeys}
              mode="inline"
              items={menuItems.map((item) => {
                return {
                  key: item.key,
                  icon: item.icon,
                  label: <Link href={item.url}>{item.label}</Link>,
                  children: item.children?.map(child => {
                    return {
                      key: child.key,
                      icon: child.icon,
                      label: <Link href={child.url}>{child.label}</Link>
                    }
                  })
                };
              })}
            />
          </Sider>
          <Layout>
            <Header style={{ padding: '12px', background: colorBgContainer }} className="flex justify-end">
                 <p className="mr-4">当前地址: <span className="text-green-400">{ baseUrl || '未设置' }</span></p>
                 <BaseUrlCard isVisible={ visible } baseUrl={ baseUrl } /> 
            </Header>
            <Content style={{ margin: "0 16px" }}>
              { baseUrl !== "" && 
              <>
                <ActiveModal isOpen={!isActived} />
                <GlobalContext.Provider value={{ baseUrl }}>
                  {children}
                </GlobalContext.Provider>
                </> 
              }
            </Content>
            <Footer style={{ textAlign: "center" }}>
              路谱智迅 ©{new Date().getFullYear()} Created by 路谱智迅
            </Footer>
          </Layout>
        </Layout>
      </body>
    </html>
  );
}
