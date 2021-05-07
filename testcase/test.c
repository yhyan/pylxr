#ifdef USLEEP
	else {
	    if (!disconnect && hostdata->time_expires && jiffies >
		hostdata->time_expires) {
		hostdata->time_expires = jiffies + USLEEP_SLEEP;
#if (NDEBUG & NDEBUG_USLEEP)
		printk("scsi%d : poll timed out, sleeping until %ul\n", instance->host_no,
		    hostdata->time_expires);
#endif
		NCR5380_set_timer (instance);
		return;
	    }
	}
#endif