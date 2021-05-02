#ifndef _SYS_STAT_H
#define _SYS_STAT_H

#include <sys/types.h>

typedef int dev_t;

struct stat {
	dev_t	st_dev;
};
