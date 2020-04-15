// -*- coding: utf-8; -*-
//
// Copyright (C) 2015 - 2019 Lionel Ott
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.


import QtQuick 2.14
import QtQuick.Controls 2.14
import QtQuick.Layouts 1.14
import QtQuick.Window 2.14

import QtQuick.Controls.Universal 2.14

import gremlin.ui.device 1.0


Item {
    id: root

    property int deviceIndex: 0
    property DeviceListModel deviceListModel

    ScrollView {
        id: idScrollView
        anchors.fill: parent

        ListView
        {
            id: idDeviceList
            anchors.fill: parent
            orientation: ListView.Horizontal

            model: deviceListModel
            delegate: idDeviceDelegate

            onCurrentIndexChanged: root.deviceIndex = currentIndex

            boundsBehavior: Flickable.StopAtBounds
        }

        Component {
            id: idDeviceDelegate

            Label {
                id: idDeviceName

                text: name
                leftPadding: 20
                rightPadding: 20
                topPadding: 10
                bottomPadding: 10

                background: Rectangle {
                    color: model.index == idDeviceList.currentIndex ? Universal.chromeMediumColor : Universal.background
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: idDeviceList.currentIndex = model.index
                }
            }
        } // Component
    } // ScrollView
} // Item