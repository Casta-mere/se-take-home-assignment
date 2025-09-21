## Basic Test

```bash
{
  printf "help\n";
  printf "+bot\n";
  printf "new-normal\n";
  printf "status\n";
  sleep 11;
  printf "status\n";
  printf "exit\n";
} | python3 -m app.main
```

expected order: 1

## VIP / Normal Order Test

```bash
{
  printf "new-normal\n";
  printf "new-vip\n";
  printf "status\n";
  printf "+bot\n";
  sleep 22;
  printf "status\n";
  printf "exit\n";
} | python3 -m app.main
```

expected order: 2, 1

## -Bot Test

```bash
{
  printf "new-normal\n";
  printf "status\n";
  printf "+bot\n";
  sleep 3;
  printf "-bot\n";
  printf "new-vip\n";
  printf "+bot\n";
  sleep 22;
  printf "status\n";
  printf "exit\n";
} | python3 -m app.main
```

expected order: 2, 1

## Multi Test

```bash
{
  printf "new-vip\n";
  printf "new-vip\n";
  printf "+bot\n";
  printf "new-normal\n";
  printf "+bot\n";
  printf "new-vip\n";
  sleep 22;
  printf "status\n";
  printf "exit\n";
} | python3 -m app.main
```

expected order: 1, 2, 4, 3
