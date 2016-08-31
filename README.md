A simple python script to monitor state of a headless weewx server (internet connection, meteo data).
It sends administrative emails or reboots the server as needed.
Небольшой python скрипт для мониторинга состояния сервера weewx (интернет соединение, метеоданные).
Отправляет email сообщения администратору или перезагружает сервер при необходимости.

### Требования к системе
* Linux с установленным python (протестировано на Ubuntu 16.04, python 2.7 и 3.5)
* Установленный и настроенный weewx (http://www.weewx.com/)
* Supervisord
* Аккаунт, для которого в sudoers разрешена перезагрузка без пароля

## Установка и настройка (Ubuntu 16.04)

Предполагается, что текущее имя пользователя `meteo`. Если это не так, нужно
будет откорректировать настройки в файле `meteo_check_status.conf` (см. далее).

Обновляем информацию о пакетах
```
apt-get update
```

Скачиваем и устанавливаем weewx. Уточнить текущую версию на http://weewx.com/downloads/.
На момент написания данного текста это была версия 3.5.1
```
wget http://weewx.com/downloads/weewx_3.5.0-1_all.deb
sudo dpkg -i weewx_3.5.0-1_all.deb
sudo apt-get -f -y install
```

Настройки в файле `/etc/weewx/weewx.conf`

Устанавливаем supervisord
```
sudo apt-get -y install supervisor
```

Разрешаем пользователю `meteo` перезапуск без ввода пароля
```
sudo visudo
```
Добавить строку (если имя пользователя не meteo, то заменить)
```
meteo ALL=NOPASSWD: /sbin/shutdown -r +1
```

Скачиваем скрип мониторинга
```
cd ~
git clone https://github.com/cheretbe/meteo-scripts.git
```

Настраиваем работу скрипта в качестве сервиса. Если имя пользователя не `meteo`,
то нужно откорректировать настройки в файле `/etc/supervisor/conf.d/meteo_check_status.conf`.
```
sudo cp ~/meteo-scripts/meteo_check_status.conf /etc/supervisor/conf.d/
```

Если нужны дополнительные параметры (например, `--debug`), добавляем их к командной
строке в `/etc/supervisor/conf.d/meteo_check_status.conf`. Список параметров можно посмотреть
с помощью `meteo-scripts/meteo_check_status.py --help`

По умолчанию сервис supervisor не запущен.
```
sudo systemctl enable supervisor.service
sudo service supervisor start
```

Лог скрипта находится в файле `/var/log/supervisor/meteo_check_status.log`
Остановить или запустить только скрипт, не затрагивая другие сервисы superviosrd
(если есть):
```
sudo supervisorctl stop meteo_check_status
sudo supervisorctl start meteo_check_status
```