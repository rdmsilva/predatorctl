[English](README.md) | **Português (BR)**

# predatorctl

Central de controle GTK4/libadwaita para notebooks gamer **Acer Predator** (e Nitro) no Linux: temperaturas ao vivo, controle de ventoinha, perfis térmicos (incluindo Turbo), RGB do teclado em 4 zonas e proteção de bateria — com uma **superfície de privilégio deliberadamente mínima** (sem regra polkit sem senha, sem módulo de kernel próprio, sem daemon root).

> A interface do aplicativo é em inglês.

![Dashboard do predatorctl](screenshots/dashboard.png)

## Funcionalidades

- **Dashboard** — mostradores radiais de temperatura de CPU / GPU / NVMe / RAM, telemetria da GPU (uso, potência, clock, ventoinha), modo atual da ventoinha e perfil térmico.
- **Temperaturas** — gráfico de histórico do package da CPU e sparklines por núcleo.
- **Ventoinha** — automático (EC controla) ou manual CPU/GPU (0–100%), além do botão "Máximo" para emergências.
- **Perfis térmicos** — os perfis Acer reais (Eco / Equilibrado / Performance / Turbo) via `platform_profile`. Performance e Turbo são bloqueados pelo firmware quando na bateria (mesmo comportamento do PredatorSense oficial); a UI os desabilita fora da tomada em vez de falhar silenciosamente.
- **RGB do teclado** — efeitos animados em 4 zonas (respiração, neon, onda, deslize, zoom) com cor, brilho e velocidade.
- **Bateria** — leitura de carga/potência/tensão, limitador de carga em 80%, LCD override.

### Capturas de tela

| Temperaturas | Ventoinha |
|---|---|
| ![Página de temperaturas](screenshots/temperatures.png) | ![Página da ventoinha](screenshots/fan.png) |

| Perfis térmicos | RGB do teclado |
|---|---|
| ![Página de perfis](screenshots/profile.png) | ![Página de RGB](screenshots/rgb.png) |

| Bateria | |
|---|---|
| ![Página da bateria](screenshots/battery.png) | |

Os sensores são auto-detectados por *tipo* de chip via `sensors -j` (`coretemp` Intel ou `k10temp`/`zenpower` AMD, qualquer NVMe, RAM `spd5118`/`jc42`, NVIDIA via `nvidia-smi` com fallback `amdgpu`), então a leitura de temperaturas funciona em toda a família Predator/Nitro — desenvolvido e testado num **Predator Helios Neo 16 (PHN16-72)**. Os *controles* de hardware exigem a interface sysfs do `linuwu_sense` (veja abaixo); em máquinas não suportadas as leituras mostram `N/A` e as escritas falham de forma limpa.

## Modelo de segurança (a razão de existir)

As ferramentas existentes para este hardware costumam exigir uma quantidade assustadora de confiança: regras polkit sem senha, módulos de kernel fora da árvore, acesso direto ao Embedded Controller, instaladores `curl | sudo bash`. O predatorctl foi escrito do zero para evitar tudo isso:

- **Leituras são não-privilegiadas.** Toda a telemetria vem de sysfs legível por qualquer usuário e de comandos comuns (`sensors`, `nvidia-smi`).
- **Escritas passam por um único helper minúsculo** (`helper/predatorctl-helper`, ~130 linhas — leia!). É o *único* código que roda como root. Ele se recusa a rodar sem root, só escreve numa whitelist fixa de caminhos sysfs e valida estritamente cada valor antes de escrever.
- **Nenhuma escalação sem senha.** A regra polkit concede `auth_admin_keep`: você digita a senha uma vez e ela fica em cache por ~5 minutos, como o sudo. A regra só casa com o helper instalado (root-owned).
- **Nenhum código de kernel próprio.** Ele usa o módulo open-source desenvolvido independentemente [linuwu_sense](https://github.com/0x7375646F/Linuwu-Sense), que você instala por conta própria.

## Compatibilidade

**Hardware** — os controles exigem um notebook suportado pelo [`linuwu_sense`](https://github.com/0x7375646F/Linuwu-Sense#supported-models):

| Notebook | Status |
|---|---|
| Predator Helios Neo 16 (PHN16-72) | ✅ Totalmente testado (máquina de desenvolvimento) |
| Outros Predators suportados pelo linuwu_sense | ✅ Deve funcionar por completo (mesmo sysfs `predator_sense`) |
| Modelos Nitro suportados pelo linuwu_sense | ⚠️ Temperaturas, perfis térmicos e RGB do teclado devem funcionar; controle de ventoinha e limitador de bateria ficam sob `nitro_sense`, ainda não mapeado (escritas falham de forma limpa) — contribuições bem-vindas |
| Qualquer outro notebook | 📊 Telemetria somente-leitura (temperaturas via `lm_sensors`/`nvidia-smi`); controles mostram `N/A` e falham de forma limpa |

**Software** — qualquer distribuição Linux com GTK4 + **libadwaita ≥ 1.4**, polkit moderno (`rules.d` em JS) e Python ≥ 3.10:

| Distribuição | Status | Pacotes |
|---|---|---|
| Arch / Manjaro | ✅ Testado | `python-gobject gtk4 libadwaita lm_sensors polkit` |
| Ubuntu 24.04+ / Debian 13+ | ✅ Deve funcionar | `python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 lm-sensors polkitd` |
| Fedora 39+ | ✅ Deve funcionar | `python3-gobject gtk4 libadwaita lm_sensors polkit` |
| Ubuntu 22.04 | ❌ | libadwaita 1.1 é antiga demais (o app usa widgets da 1.4) |

O desktop environment não importa (GNOME, KDE Plasma, etc., X11 ou Wayland) — o app traz seu próprio tema escuro "instrument" de qualquer forma.

## Requisitos

- Um notebook Acer Predator/Nitro suportado pelo [`linuwu_sense`](https://github.com/0x7375646F/Linuwu-Sense), com o módulo carregado (ele substitui o `acer_wmi` da árvore do kernel). Você pode seguir as instruções daquele projeto, ou usar o helper **opcional** incluído aqui, que o configura com DKMS para que atualizações de kernel não o removam silenciosamente:

  ```bash
  sudo ./install-linuwu-dkms.sh                       # clona o upstream e instala via DKMS
  sudo ./install-linuwu-dkms.sh ~/src/Linuwu-Sense    # ou use um checkout local que você auditou
  sudo ./install-linuwu-dkms.sh --uninstall           # desfaz tudo (acer_wmi volta no reboot)
  ```

  (também disponível como `sudo make linuwu [LINUWU_SRC=~/src/Linuwu-Sense]`)
- Pacotes do sistema (não é um projeto pip — o PyGObject vincula ao GTK do sistema):
  - `python-gobject`, `gtk4`, `libadwaita` (nomes do Arch; use os equivalentes da sua distro)
  - `lm_sensors` (para o `sensors -j`)
  - `nvidia-utils` (opcional, para telemetria de GPU NVIDIA)
  - `polkit` (para o `pkexec`)

## Rodando da fonte

```bash
git clone https://github.com/rdmsilva/predatorctl.git
cd predatorctl
python3 src/main.py    # ou: make run
```

Rodando da fonte, cada escrita de hardware pede sua senha (a regra polkit só casa com o caminho instalado — ótimo para experimentar).

## Instalando

```bash
sudo ./install.sh      # ou: sudo make install
predatorctl            # ou abra "Predator Control" no menu de aplicativos
```

Isso instala em `/usr/local/lib/predatorctl` mais o launcher, a entrada de menu e a regra polkit.

O instalador copia o app para um diretório root-owned (um script executado como root mas gravável pelo usuário seria um vetor de escalação), registra a entrada `.desktop`/ícone e instala a regra polkit `auth_admin_keep` para membros de `wheel`/`sudo`.

```bash
sudo ./uninstall.sh    # ou: sudo make uninstall
```

### Restaurando preferências no boot

O `linuwu_sense` recarrega com os defaults do driver a cada boot, e o predatorctl não tem daemon em segundo plano — então, sem isso, seu último perfil térmico, efeito de RGB e limitador de bateria seriam perdidos até você reabrir o app e configurar de novo.

O `install.sh` instala e habilita uma unit systemd `predatorctl-restore.service` que reaplica os valores salvos no boot, e não há nada pra configurar: toda vez que você muda um ajuste no app, o `predatorctl-helper` espelha o valor em `/etc/predatorctl/restore.conf`, então ele já está lá pro próximo boot. A unit é condicionada por `ConditionPathExists=/etc/predatorctl/restore.conf`, então numa instalação nova (antes de você mudar qualquer coisa) ela é um no-op inofensivo.

Mantém a mesma fronteira de privilégio de tudo o resto. A escrita espelhada acontece dentro do próprio `predatorctl-helper` — o valor já passou pela whitelist e pelo `validate()` para a escrita real no sysfs um instante antes, então escrever a mesma string num segundo caminho fixo não é uma superfície de injeção nova. No boot, a unit roda como root diretamente (não há sessão interativa pra pedir senha, então não dá pra passar por `pkexec`), mas o `predatorctl-restore` não escreve em sysfs nenhum — só lê o config e chama o mesmo helper. `/etc/predatorctl/restore.conf` é root-owned e não gravável pelo usuário comum, então não dá pra usar isso pra contrabandear escritas arbitrárias em nenhuma das duas etapas.

Normalmente você nunca precisa tocar nesse arquivo; `data/restore.conf.example` documenta o formato caso queira adicionar uma entrada que o app não cobre.

## Testes

Não precisa de hardware — parsers, validação e formatos de valores são testados com tudo mockado:

```bash
make test          # ou: python3 -m unittest discover tests -v
```

(`make help` lista os outros atalhos: `run`, `install`, `uninstall`, `clean`.)

## Arquitetura

Hexagonal (ports & adapters), organizada em torno da única fronteira que importa — leituras não-privilegiadas vs. escritas privilegiadas:

```
src/domain/      modelos + portas (SensorPort leitura / ControlPort escrita) — sem GTK, sem sysfs
src/adapters/    sysfs_sensors.py (leituras), pkexec_control.py (escritas via pkexec)
src/ui/          páginas GTK4/libadwaita (dashboard, temperaturas, ventoinha, perfil, rgb, bateria)
helper/          predatorctl-helper — o único código que roda como root
                 predatorctl-restore — restauração opcional de preferências no boot, chama o helper acima
data/            entrada .desktop, ícone, regra polkit, predatorctl-restore.service + config de exemplo
```

`src/main.py` é o composition root: troque os adapters por fakes ali e toda a UI roda sem o hardware. Veja o `CLAUDE.md` para um tour mais profundo (formatos de valores, modelo de threading, peculiaridades do hardware).

## Aviso

Este software escreve nos controles de ventoinha e térmicos expostos pelo firmware do seu notebook através do `linuwu_sense`. Ele usa apenas interfaces que o software do próprio fabricante usa, e valida tudo que escreve — mas, como toda ferramenta de controle de hardware, **use por sua conta e risco**.

## Créditos

- [0x7375646F/Linuwu-Sense](https://github.com/0x7375646F/Linuwu-Sense) — o driver de kernel que torna tudo isso possível.

## Licença

[GPL-3.0-or-later](LICENSE)
