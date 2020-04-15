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
import QtQuick.Window 2.14
import QtQuick.Layouts 1.14

import gremlin.ui.device 1.0

import "helpers.js" as Helpers


ApplicationWindow {

    // Basic application setup
    title: "Joystick Gremlin"
    width: 1000
    height: 680
    visible: true
    id: root


    // Menu bar with all its entries
    menuBar: MenuBar {
        Menu {
            title: qsTr("File")

            MenuItem {
                text: qsTr("New Profile")
                onTriggered: console.log("Test")
            }
            MenuItem {
                text: qsTr("Load Profile")
                onTriggered: console.log("Test")
            }

            Menu {
                title: qsTr("Recent")
            }

            MenuItem {
                text: qsTr("Save Profile")
                onTriggered: console.log("Test")
            }
            MenuItem {
                text: qsTr("Save Profile As")
                onTriggered: console.log("Test")
            }
            MenuItem {
                text: qsTr("Exit")
                onTriggered: Qt.quit();
            }
        }
        Menu {
            title: qsTr("Tools")

            MenuItem {
                text: qsTr("Manage Modes")
                onTriggered: Helpers.createComponent("DialogManageModes.qml")
            }
            MenuItem {
                text: qsTr("Input Repeater")
                //onTriggered: Helpers.createComponent(".qml")
            }
            MenuItem {
                text: qsTr("Device Information")
                onTriggered: Helpers.createComponent("DialogDeviceInformation.qml")
            }
            MenuItem {
                text: qsTr("Calibration")
                onTriggered: Helpers.createComponent("DialogCalibration.qml")
            }
            MenuItem {
                text: qsTr("Input Viewer")
                onTriggered: Helpers.createComponent("DialogInputViewer.qml")
            }
            MenuSeparator {}
            MenuItem {
                text: qsTr("PDF Cheatsheet")
                onTriggered: Helpers.createComponent("DialogPDFCheatsheet.qml")
            }
            MenuSeparator {}
            MenuItem {
                text: qsTr("Options")
                onTriggered: Helpers.createComponent("DialogOptions.qml")
            }
            MenuItem {
                text: qsTr("Log Display")
                onTriggered: Helpers.createComponent("DialogLogDisplay.qml")
            }
        }

        Menu {
            title: qsTr("Help")

            MenuItem {
                text: qsTr("About")
                onTriggered: Helpers.createComponent("DialogAbout.qml")
            }
        }
    }

    DeviceListModel {
        id: idDeviceListModel
    }


    // Main content area
    ColumnLayout
    {
        anchors.fill: parent

        // List of all detected devices
        DeviceList {
            id: idDevicePanel
            Layout.preferredHeight: 50
            Layout.fillWidth: true


            deviceListModel: idDeviceListModel
        }

        SplitView {
            id: idContentLayout
            Layout.fillHeight: true
            Layout.fillWidth: true
            orientation: Qt.Horizontal

            // One layout per device containint all inputs of the device
            StackLayout {
                id: idInputPanel

                currentIndex: idDevicePanel.deviceIndex

                SplitView.minimumWidth: 200

                Repeater {
                    id: idDeviceInputListRepeater
                    model: idDeviceListModel

                    DeviceInputList {
                        deviceGuid: model.guid

                        //onInputIndexChanged: actionPanel.currentIndex = inputIndex
                        onInputIndexChanged: {
                            idInputConfigurationPanel.inputItemModel = backend.getInputItem(inputIdentifier)
                            idInputConfigurationPanel.libraryItemListModel = idInputConfigurationPanel.inputItemModel.libraryItems
                        }
                    }
                }
            }

            // Configuration of the selected input
            InputConfiguration {
                id: idInputConfigurationPanel
            }

        } // SplitView
    } // RowLayout
} // ApplicationWindow