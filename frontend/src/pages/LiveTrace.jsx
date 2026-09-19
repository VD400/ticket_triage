import {useEffect, useState} from 'react';
import { bucketTickets, toTitleCase, timeAgo, PRIORITY_STYLES } from "../components/dashboard/ticketBuckets";
import React from 'react';
import {useParams} from 'react-router-dom';
import useTicketWebSocket from '../hooks/useTicketWebSocket';


const LiveTrace = () => {
  const {ticketId} = useParams(); 
  const [eventLog, setEventLog] = useState([]);
  const [execState, setExecState] = useState(activeNode = null, completedNodes=[]);
  const [connection, setConnection] = useState(null);
  
  return (
    <>
      <div>
        <h3 className="text-xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">Live Trace</h3>
      </div>
    </>
  )
}

export default LiveTrace;

