import {useEffect, useState} from 'react';
import { bucketTickets, toTitleCase, timeAgo, PRIORITY_STYLES } from "../components/dashboard/ticketBuckets";
import React from 'react';
import {useParams} from 'react-router-dom';
import { useTicketWebSocket } from '../hooks/useTicketWebsSocket';


const AIActivity = () => {
  const {ticketId} = useParams(); 
  
  return (
    <div>
      
    </div>
  )
}

export default AIActivity;

