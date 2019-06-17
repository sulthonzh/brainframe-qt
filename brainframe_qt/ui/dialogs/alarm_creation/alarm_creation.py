from enum import Enum, auto
from typing import List, Dict

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QDialogButtonBox
from PyQt5.uic import loadUi

from brainframe.client.api.codecs import (
    Attribute,
    Plugin,
    Zone,
    ZoneAlarm,
    ZoneAlarmCountCondition,
    ZoneAlarmRateCondition
)
from brainframe.client.ui.resources.paths import qt_ui_paths


class ConditionType(Enum):
    COUNT = auto()
    RATE = auto()


class AlarmCreationDialog(QDialog):

    WINDOW_DURATION = 5.0
    """The default window duration for count events."""
    WINDOW_THRESHOLD = 0.5
    """The default window threshold for count events."""

    def __init__(self, zones: List[Zone],
                 plugins: List[Plugin],
                 parent=None):
        super().__init__(parent)

        loadUi(qt_ui_paths.alarm_creation_ui, self)

        self.plugins = plugins
        self.zones = zones

        self._update_combo_box(self.countable_combo_box,
                               self._detection_classes())

        # Set the behavior combo box to have initial attributes values
        detection_class = self.countable_combo_box.currentText()
        self._update_attribute_values(detection_class)
        # Update the attribute values when the behavior selection changes
        self.countable_combo_box.currentTextChanged.connect(
            self._update_attribute_values)

        self._update_combo_box(self.zone_combo_box,
                               [zone.name for zone in zones])

        # Condition type
        self.condition_type_button_group.buttonClicked.connect(
            self.condition_type_button_changed)
        self.condition_type = None
        self.set_condition_type(ConditionType.COUNT)

        # Input sanitation
        self.alarm_name.textEdited.connect(self.verify_inputs_valid)
        self.behavior_combo_box.currentTextChanged.connect(
            self.verify_inputs_valid)
        self.verify_inputs_valid()

    def condition_type_button_changed(self):
        checked_button = self.condition_type_button_group.checkedButton()
        if checked_button is self.count_based_button:
            self.set_condition_type(ConditionType.COUNT)
        elif checked_button is self.rate_based_button:
            self.set_condition_type(ConditionType.RATE)

    def set_condition_type(self, condition_type: ConditionType):
        if condition_type == ConditionType.COUNT:
            self.hide_count_widgets(False)
            self.hide_rate_widgets(True)
            self._update_combo_box(
                self.test_type_combo_box,
                ZoneAlarmCountCondition.TestType.values())
            self.count_spin_box.setMinimum(0)
        if condition_type == ConditionType.RATE:
            self.hide_count_widgets(True)
            self.hide_rate_widgets(False)
            self._update_combo_box(self.test_type_combo_box,
                                   ZoneAlarmRateCondition.TestType.values())
            self.count_spin_box.setMinimum(1)

        self.condition_type = condition_type

    def hide_count_widgets(self, hidden):
        """Hide widgets used when using count conditions"""
        self.behavior_combo_box.setHidden(hidden)
        self.in_count_label.setHidden(hidden)

    def hide_rate_widgets(self, hidden):
        """Hide widgets used when using rate conditions"""
        self.direction_combo_box.setHidden(hidden)
        self.in_rate_label.setHidden(hidden)
        self.duration_spin_box.setHidden(hidden)
        self.seconds_label.setHidden(hidden)

    @classmethod
    def new_alarm(cls, *, zones, plugins: List[Plugin]):
        dialog = cls(zones, plugins, None)
        result = dialog.exec_()

        zones = {zone.name: zone for zone in zones}  # type: List[Zone]

        if not result:
            return None, None

        alarm_name = dialog.alarm_name.text()
        condition_button = dialog.condition_type_button_group.checkedButton()
        test_type = dialog.test_type_combo_box.currentText()
        count = dialog.count_spin_box.value()
        countable = dialog.countable_combo_box.currentText()
        zone = dialog.zone_combo_box.currentText()
        start_time = dialog.start_time_edit.time().toString("HH:mm:ss")
        stop_time = dialog.stop_time_edit.time().toString("HH:mm:ss")

        count_condition = []
        rate_condition = []

        if condition_button is dialog.count_based_button:
            behavior = dialog.behavior_combo_box.currentText()

            # Find the category that the attribute value is a part of
            attribute_category = None
            for plugin in plugins:
                for category, values in plugin.capability.attributes.items():
                    if behavior in values:
                        attribute_category = category
                        break

            if behavior in ["", "[any]"]:
                # No behavior was selected
                attribute = None
            else:
                attribute = Attribute(category=attribute_category,
                                      value=behavior)

            count_condition.append(ZoneAlarmCountCondition(
                test=test_type,
                check_value=count,
                with_class_name=countable,
                with_attribute=attribute,
                window_duration=AlarmCreationDialog.WINDOW_DURATION,
                window_threshold=AlarmCreationDialog.WINDOW_THRESHOLD))

        elif condition_button is dialog.rate_based_button:
            direction = dialog.direction_combo_box.currentText()
            duration = dialog.duration_spin_box.value()

            if direction == "enter":
                direction = ZoneAlarmRateCondition.DirectionType.ENTERING
            elif direction == "exit":
                direction = ZoneAlarmRateCondition.DirectionType.EXITING
            elif direction == "enter/exit":
                direction = \
                    ZoneAlarmRateCondition.DirectionType.ENTERING_OR_EXITING

            rate_condition.append(ZoneAlarmRateCondition(
                test=test_type,
                change=count,
                direction=direction,
                duration=duration,
                with_class_name=countable,
                with_attribute=None))

        else:
            raise ValueError(f"Invalid condition button checked: "
                             f"'{condition_button.currentText()}'")

        alarm = ZoneAlarm(name=alarm_name,
                          zone_id=zones[zone].id,
                          count_conditions=count_condition,
                          rate_conditions=rate_condition,
                          active_start_time=start_time,
                          active_end_time=stop_time,
                          use_active_time=True)  # TODO(Bryce Beagle): False?

        zones[zone].alarms.append(alarm)

        return zones[zone], alarm

    @pyqtSlot()
    def verify_inputs_valid(self):
        """Return True or false if the inputs are valid"""
        is_valid = True
        if self.alarm_name.text().strip() == "":
            is_valid = False
        # Check to make sure the necessary combo boxes have selections. This
        # also prevents the user from creating alarms when no classes are
        # available
        if self.condition_type == ConditionType.COUNT:
            if self.countable_combo_box.currentIndex() == -1 or \
                    self.behavior_combo_box.currentIndex() == -1:
                is_valid = False
        elif self.condition_type == ConditionType.RATE:
            if self.countable_combo_box.currentIndex() == -1 or \
                    self.direction_combo_box.currentIndex() == -1:
                is_valid = False

        self.dialog_button_box.button(QDialogButtonBox.Ok).setEnabled(is_valid)

    @pyqtSlot(str)
    def countable_index_changed(self, countable):
        self._update_combo_box(self.behavior_combo_box,
                               self._attribute_values(countable))

    @classmethod
    def _update_combo_box(cls, combo_box, items):
        combo_box.clear()
        combo_box.insertItems(0, items)

    def _update_attribute_values(self, detection_class):
        attributes_for_class = self._attributes_for_class(detection_class)

        if detection_class:
            # Get all attribute values a detection_class can have
            attribute_values = [vals for vals in attributes_for_class.values()]

            # Sum all lists and add also add empty entry
            attribute_values = sum(attribute_values, ['[any]'])
            self._update_combo_box(self.behavior_combo_box,
                                   attribute_values)

    def _detection_classes(self) -> List[str]:
        """Inspects plugins to find all detectable classes.

        :return: All currently detectable class names
        """
        detection_classes = set()
        for plugin in self.plugins:
            for det_class in plugin.capability.detections:
                detection_classes.add(det_class)

        return list(detection_classes)

    def _attributes_for_class(self, class_name) -> Dict[str, List[str]]:
        """Gets all attributes the given class name can have alongside all
        possible values.

        {
            "gender": ["masculine", "feminine", "unknown"],
            "age": ["old", "young"]
        }

        :param class_name: The class name to find attributes for
        :return: A dict whose keys are attribute categories and whose values
            are the corresponding list of possible attribute values
        """
        attributes = {}
        for plugin in self.plugins:
            if class_name in plugin.output_type.detections:
                for category, values in plugin.capability.attributes.items():
                    attributes[category] = values

        return attributes

    def _attribute_values(self, category) -> List[str]:
        """Gets all possible values for the given attribute category.

        :param category: The attribute category to find values for
        :return: All possible values
        """
        values = set()
        for plugin in self.plugins:
            if category in plugin.capability.attributes:
                for value in plugin.capability.attributes[category]:
                    values.add(value)

        return list(values)
