# Bedrock Desktop Setup

Неофициальная интеграция BedrockOnLinux для CachyOS + Hyprland. Создаёт два ярлыка:
`Minecraft Bedrock` (play) и `Minecraft Bedrock Launcher` (gui).

Сам лаунчер, Minecraft, аккаунты и миры не входят в проект.
Оригинальный проект: https://github.com/Wyze3306/BedrockOnLinux
Загрузки: https://github.com/Wyze3306/BedrockOnLinux/releases/latest

## Требования и установка

Linux, Python 3.10+ и отдельно скачанный исполняемый AppImage BedrockOnLinux.
Нужна своя лицензия Minecraft для Windows и собственный Microsoft-аккаунт.
Зависимости игры устанавливаются по инструкции оригинального проекта.
Не запускайте этот установщик через sudo.

```sh
git clone https://github.com/Arytemu/bedrock-desktop-setup.git
cd bedrock-desktop-setup
python3 desktop_setup.py install "/полный/путь/к/BedrockOnLinux.AppImage"
```

Замените путь на настоящий. AppImage должен иметь разрешение на выполнение
(`chmod +x`) и находиться в постоянной папке, например ~/Applications.
Установщик не скачивает и не запускает игру, не проверяет подлинность AppImage.
После установки закройте и заново откройте меню приложений.
Старые ярлыки не изменяются и могут остаться рядом.

## Что исправляется

Удаляются только LD_PRELOAD и LD_LIBRARY_PATH из окружения запускаемой игры/GUI.
Остальное окружение сохраняется. DMS, Hyprland и fish не изменяются.
Это обход ошибки запуска из DMS, которая в проверенном случае проявлялась как
`/bin/sh: error while loading shared libraries: libQt6QuickControls2.so.6`.
Он не гарантирует исправление всех сбоев BedrockOnLinux.
Иконка куба создана для проекта и не является официальным логотипом Minecraft.

## Обновление, журналы и удаление

Если изменили путь AppImage, повторите install с новым путём.

```sh
python3 desktop_setup.py status
tail -n 80 ~/.local/state/bedrock-desktop-setup/logs/game.log
tail -n 80 ~/.local/state/bedrock-desktop-setup/logs/launcher.log
python3 desktop_setup.py uninstall
```

Перед удалением закройте игру/GUI. Удаляются только неизменённые файлы интеграции;
AppImage, игра, аккаунты, миры и журналы остаются. Чужие или изменённые файлы
не перезаписываются. Журналы дописываются и могут расти: не публикуйте токены,
коды входа и личные данные из них.

Поддерживаются XDG_DATA_HOME и XDG_STATE_HOME. По умолчанию данные интеграции
лежат в ~/.local/share/bedrock-desktop-setup, ярлыки в ~/.local/share/applications,
скрипты в ~/.local/bin. Журналы лежат в XDG_STATE_HOME/bedrock-desktop-setup/logs.

## Тесты и лицензия

```sh
python3 -m unittest discover -s tests -v
```

Тесты используют поддельный AppImage, не Minecraft. Проверка на реальном
CachyOS/Hyprland всё ещё требуется. Код и оригинальная иконка: MIT, Arytemu, 2026.
BedrockOnLinux принадлежит его авторам и распространяется отдельно.
Minecraft принадлежит Mojang/Microsoft. Проект не связан с Mojang/Microsoft.
