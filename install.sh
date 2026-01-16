#!/usr/bin/env bash
set -e

REPO="https://github.com/veplix/Hyprland-dotfiles.git"
DEST="$HOME/Hyprland-dotfiles"

echo "===== ОБНОВЛЕНИЕ СИСТЕМЫ ====="
sudo pacman -Syu --noconfirm

echo "===== БАЗА ====="
sudo pacman -S --needed --noconfirm \
    git base-devel linux-headers \
    networkmanager

sudo systemctl enable NetworkManager.service

echo "===== NVIDIA (DKMS) ====="
sudo pacman -S --needed --noconfirm \
    nvidia-dkms \
    nvidia-utils \
    nvidia-settings \
    lib32-nvidia-utils

echo "===== WAYLAND + HYPRLAND ====="
sudo pacman -S --needed --noconfirm \
    hyprland \
    xdg-desktop-portal-hyprland \
    wayland wayland-protocols wlroots \
    polkit-kde-agent

echo "===== SDDM ====="
sudo pacman -S --needed --noconfirm \
    sddm \
    qt5-graphicaleffects \
    qt5-quickcontrols2 \
    qt5-svg

sudo systemctl enable sddm.service

echo "===== МИНИМУМ ДЛЯ РАБОТЫ ====="
sudo pacman -S --needed --noconfirm \
    alacritty \
    waybar \
    rofi \
    neovim \
    zsh \
    pavucontrol \
    pipewire pipewire-pulse wireplumber \
    grim slurp wl-clipboard \
    brightnessctl \
    playerctl \
    xfce4-power-manager \
    bluez bluez-utils

sudo systemctl enable bluetooth.service

echo "===== ШРИФТЫ ====="
sudo pacman -S --needed --noconfirm \
    ttf-jetbrains-mono \
    ttf-font-awesome \
    noto-fonts \
    noto-fonts-emoji

echo "===== AUR (yay) ====="
if ! command -v yay >/dev/null 2>&1; then
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    (cd /tmp/yay && makepkg -si --noconfirm)
fi

yay -S --needed --noconfirm \
    nerd-fonts-complete \
    oh-my-zsh-git \
    powerlevel10k

echo "===== ZSH ====="
chsh -s /bin/zsh "$USER"

echo "===== DOTFILES ====="
if [ -d "$DEST" ]; then
    (cd "$DEST" && git pull)
else
    git clone "$REPO" "$DEST"
fi

echo "===== КОПИРОВАНИЕ КОНФИГОВ ====="
rsync -a --backup \
  --backup-dir="$HOME/dotfiles_backup_$(date +%s)" \
  "$DEST/.config/" "$HOME/.config/"

cp -f "$DEST/.zshrc" "$HOME/.zshrc" 2>/dev/null || true
cp -f "$DEST/.p10k.zsh" "$HOME/.p10k.zsh" 2>/dev/null || true

echo "===== ТЕМЫ / ИКОНКИ / ОБОИ ====="
mkdir -p ~/.themes ~/.icons ~/.wallpapers

cp -r "$DEST/.themes/"* ~/.themes/ 2>/dev/null || true
cp -r "$DEST/.icons/"* ~/.icons/ 2>/dev/null || true
cp -r "$DEST/.wallpapers/"* ~/.wallpapers/ 2>/dev/null || true

echo "===== NVIDIA FIX (Wayland) ====="
sudo mkdir -p /etc/modprobe.d
echo "options nvidia_drm modeset=1" | sudo tee /etc/modprobe.d/nvidia.conf

echo "===== ГОТОВО ====="
echo "1) Перезагрузи ПК"
echo "2) В SDDM выбери сессию Hyprland"
echo "3) SUPER + ENTER — терминал"
