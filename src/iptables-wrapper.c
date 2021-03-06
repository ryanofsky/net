#include <stdio.h>
#include <string.h>
#include <unistd.h>

const char * IPTABLES_PATH = "/sbin/iptables";

void usage()
{
  fprintf(stderr, 
          "Usage: iptables-wrapper \"append\"|\"delete\" table chain action\n"
          "                        \"src\"|\"dst\" ip_addr|\"none\" mac_addr|"
	  "\"none\"\n\n"
          "       iptables-wrapper \"show\"|\"zero\" table\n\n" 
      
      );
  fprintf(stderr, "A wrapper around iptables that accepts a restricted "
                  "set of arguments\nand can be set suid root.\n");
}

int valid_chains(char * table, char * chain, char * action)
{
  int valid = 1;
  if (strcmp(table, "filter") == 0)
  {
    if (strcmp(chain, "ACCEPT_REGISTERED_SRC") != 0
        && strcmp(chain, "ACCEPT_REGISTERED_DST") != 0
        && strcmp(chain, "MAYBE_BLACKOUT") != 0)
    {
      fprintf(stderr, "Error: invalid chain `%s' for filter table\n", chain);
      valid = 0;
    }
    if (strcmp(action, "ACCEPT") != 0 && strcmp(action, "DROP") != 0)
    {
      fprintf(stderr, "Error: invalid action `%s' for filter table\n", action);
      valid = 0;
    }
  }
  else if (strcmp(table, "nat") == 0)
  {
    if (strcmp(chain, "REDIRECT_BLOCKED") != 0
        && strcmp(chain, "ACCEPT_REGISTERED") != 0
        && strcmp(chain, "MAYBE_BLACKOUT") != 0)
    {
      fprintf(stderr, "Error: invalid chain `%s' for nat table\n", chain);
      valid = 0;
    }
    if (strcmp(action, "ACCEPT") != 0 
        && strcmp(action, "BLOCK") != 0
        && strcmp(action, "BLACKOUT") != 0)
    {
      fprintf(stderr, "Error: invalid action `%s' for nat table\n", action);
      valid = 0;
    }
  }
  else
  {
    fprintf(stderr, "Error: invalid table `%s'\n", table);
    valid = 0;
  }
  return valid;
}

int eat_digits(char ** str, int min, int max, int hex)
{
  int n = 0;
  while (**str && strchr(hex ? "0123456789ABCDEFabcdef" 
                             : "0123456789", **str))
  {
    ++n; ++*str;
    if (n >= max)
      break;
  }
  return n >= min && n <= max;
}

int eat_sep(char ** str, char sep)
{
  if (**str == sep)
  {
    ++*str;
    return 1;
  }
  else
    return 0;
}

int valid_ip(char * ip)
{
  return eat_digits(&ip, 1, 3, 0)
         && eat_sep(&ip, '.') 
         && eat_digits(&ip, 1, 3, 0)
         && eat_sep(&ip, '.')
         && eat_digits(&ip, 1, 3, 0)
         && eat_sep(&ip, '.')
         && eat_digits(&ip, 1, 3, 0)
         && eat_sep(&ip, '\0');
}

int valid_mac(char * mac)
{
  return eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, ':')
         && eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, ':')
         && eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, ':')
         && eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, ':')
         && eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, ':')
         && eat_digits(&mac, 2, 2, 1)
         && eat_sep(&mac, '\0');
}

int main(int argc, char **argv)
{
  enum { APPEND, DELETE, SHOW, INVALID } mode = INVALID;
  char *mac, *ip, *table, *chain, *action;
  int source, zero;
 
  if (argc == 8)
  {
    if (strcmp(argv[1], "append") == 0)
      mode = APPEND;
    else if (strcmp(argv[1], "delete") == 0)
      mode = DELETE;
    else
    {
      fprintf(stderr, "Error: invalid mode `%s'\n", argv[1]);
      return 1;
    }

    if (valid_chains(argv[2], argv[3], argv[4]))
    {
      table = argv[2];
      chain = argv[3];
      action = argv[4];
    }
    else
      return 1;

    if (strcmp(argv[5], "src") == 0)
      source = 1;
    else if (strcmp(argv[5], "dst") == 0)
      source = 0;
    else
    {
      fprintf(stderr, "Error: invalid rule type `%s', must be `src' or `dst'\n",
                      argv[5]);
      return 1;
    }
    
    if (valid_ip(argv[6]))
      ip = argv[6];
    else if (strcmp(argv[6], "none") == 0)
      ip = NULL;
    else
    {
      fprintf(stderr, "Error: invalid ip `%s'\n", argv[6]);
      return 1;
    }

    if (valid_mac(argv[7]))
    {
      if (!source)
      {
        fprintf(stderr, "Error: cannot specify destination MAC address\n");
        return 1;
      }
      mac = argv[7];
    }
    else if (strcmp(argv[7], "none") == 0)
      mac = NULL;
    else
    {
      fprintf(stderr, "Error: invalid mac `%s'\n", argv[7]);
      return 1;
    }

    if (!ip && !mac && strcmp(chain, "MAYBE_BLACKOUT") != 0)
    {
      fprintf(stderr, "Error: must specify at least one ip or mac address\n");
      return 1;
    }
  }
  else if (argc == 3 && ((zero = (strcmp(argv[1], "zero") == 0)) 
                         || (strcmp(argv[1], "show") == 0)))
  {
    mode = SHOW;
    if (strcmp(argv[2], "filter") == 0)
      table = argv[2];
    else
    {
      fprintf(stderr, "Error: can't show table `%s'\n", argv[2]);
      return 1;
    }
  }
  else
  {
    usage();
    return 1;
  }

  char const * eargv[13] = { IPTABLES_PATH, "-t", table };
  int n = 3;
  if (mode == APPEND)
    eargv[3] = "-A";
  else if (mode == DELETE)
    eargv[3] = "-D";
  else if (mode == SHOW)
    eargv[3] = "-L";

  if (mode == APPEND || mode == DELETE)
  {
    eargv[++n] = chain;

    if (ip)
    {
      eargv[++n] = source ? "-s" : "-d";
      eargv[++n] = ip;
    }

    if (mac)
    {
      eargv[++n] = "-m";
      eargv[++n] = "mac";
      eargv[++n] = "--mac-source";
      eargv[++n] = mac;
    }

    eargv[++n] = "-j";
    eargv[++n] = action;  
    eargv[++n] = NULL;  
  }
  else if (mode == SHOW)
  {
    if (zero)
      eargv[++n] = "-Z";
    eargv[++n] = "-v";
    eargv[++n] = "-n";
    eargv[++n] = "-x";
    eargv[++n] = NULL;
  }
  
#if DEBUG
  int i;
  for (i = 0; i < n; ++i)
  {
    fprintf(stderr, "%s ", eargv[i]);
  }
  fprintf(stderr, "\n");
#endif
  /* XXX: casting array because execv wants non-const strings (wtf?) */
  return execv(IPTABLES_PATH, (char**)eargv);
}
