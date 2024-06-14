'use client'

import { useContext, useEffect, useState } from "react";

import { Timeline, TimelineItemProps } from 'antd';

import { GlobalContext } from "@/components/api/context";


type eventsData = {
  time: string
  person_count: number
  objects_count: number 
  pre_camera_count: number[]
}


export default function EventPage() {
  const baseUrl = useContext(GlobalContext).baseUrl
  const [ events, setEvents ] = useState<TimelineItemProps[]>([]);

  useEffect(() => {
    console.log('base url', baseUrl)
    fetch(`${baseUrl}/api/aibox_report/event/trigger/gpio`)
      .then((response) => response.json())
      .then((events_data: eventsData[]) => {
        console.log('data', events_data)
        const _events: TimelineItemProps[] = []
        for (let _event of events_data) {
          _events.push({
            label: _event.time,
            children: <><p>{`统计人数: ${_event.person_count} 人`}</p>  <p>{`检测人数: ${_event.objects_count} 人`}</p></>,
            color: _event.person_count === _event.objects_count ? 'green' : 'red'
          })
        }
        setEvents(_events)
      })
  }, [baseUrl]);

  return (
    <div className="mx-60 my-12">
      <Timeline mode='left' items={events} />
    </div>
  );

}
