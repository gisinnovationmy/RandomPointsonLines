import os
import random

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox,
    QStyle, QHBoxLayout, QGroupBox,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldExpressionWidget
from qgis.core import (
    QgsVectorLayer, QgsFeature,
    QgsGeometry, QgsPointXY, QgsWkbTypes, QgsProject,
    QgsFieldProxyModel, QgsField, QgsExpression,
    Qgis,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QMetaType
from qgis.PyQt import QtWidgets
from qgis.utils import iface
from qgis.core import QgsExpressionContext, QgsExpressionContextUtils


class RandomPointsDialog(QDialog):
    closingPlugin = pyqtSignal()
    DIALOG_TITLE = "Random Points Along Line V4.0"

    def __init__(self, iface):
        """Constructor."""
        super(RandomPointsDialog, self).__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle(self.DIALOG_TITLE)

        self.warning_shown = False
        self.mirroring = False

        self.setup_ui()
        self.update_widget_state()

        QgsProject.instance().layersAdded.connect(self.update_widget_state)
        QgsProject.instance().layersRemoved.connect(self.update_widget_state)

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        help_layout = QHBoxLayout()
        help_button = QPushButton()
        help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        )
        help_button.setToolTip("Click for help")
        help_button.clicked.connect(self.show_help)
        help_layout.addStretch()
        help_layout.addWidget(help_button)
        layout.addLayout(help_layout)

        layer_group = QGroupBox("Layer Selection")
        layer_layout = QVBoxLayout()
        layer_group.setLayout(layer_layout)

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(Qgis.LayerFilter.LineLayer)
        layer_layout.addWidget(self.layer_combo)

        self.selected_features_checkbox = QCheckBox("Use only selected features")
        self.selected_features_checkbox.setChecked(False)
        layer_layout.addWidget(self.selected_features_checkbox)

        layout.addWidget(layer_group)

        offset_group = QGroupBox("Offset Settings")
        offset_layout = QVBoxLayout()
        offset_group.setLayout(offset_layout)

        start_layout = QHBoxLayout()
        start_label = QLabel("Start Offset (%)")
        self.start_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.start_slider.setRange(0, 100)
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 100)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_slider)
        start_layout.addWidget(self.start_spin)
        offset_layout.addLayout(start_layout)

        end_layout = QHBoxLayout()
        end_label = QLabel("End Offset (%)")
        self.end_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.end_slider.setRange(0, 100)
        self.end_slider.setInvertedAppearance(True)
        self.end_spin = QSpinBox()
        self.end_spin.setRange(0, 100)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_slider)
        end_layout.addWidget(self.end_spin)
        offset_layout.addLayout(end_layout)

        mirror_reset_layout = QHBoxLayout()
        self.mirror_checkbox = QCheckBox("Mirror")
        self.mirror_checkbox.setChecked(False)
        self.reset_button = QPushButton("Reset Offsets")
        mirror_reset_layout.addWidget(self.mirror_checkbox)
        mirror_reset_layout.addWidget(self.reset_button)
        offset_layout.addLayout(mirror_reset_layout)

        layout.addWidget(offset_group)

        generation_group = QGroupBox("Point Generation Settings")
        generation_layout = QVBoxLayout()
        generation_group.setLayout(generation_layout)

        seed_layout = QHBoxLayout()
        seed_label = QLabel("Random Seed:")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setToolTip("Set a seed for reproducible results (-1 for random)")
        seed_layout.addWidget(seed_label)
        seed_layout.addWidget(self.seed_spin)
        generation_layout.addLayout(seed_layout)

        min_dist_layout = QHBoxLayout()
        min_dist_label = QLabel("Min. Distance:")
        self.min_distance_spin = QtWidgets.QDoubleSpinBox()
        self.min_distance_spin.setRange(0, 999999)
        self.min_distance_spin.setValue(0)
        self.min_distance_spin.setToolTip("Minimum distance between points (0 for no minimum)")
        min_dist_layout.addWidget(min_dist_label)
        min_dist_layout.addWidget(self.min_distance_spin)
        generation_layout.addLayout(min_dist_layout)

        self.dynamic_point_checkbox = QCheckBox("Use Field for Dynamic Point Generation")
        self.dynamic_point_checkbox.setChecked(False)
        generation_layout.addWidget(self.dynamic_point_checkbox)

        self.field_expression = QgsFieldExpressionWidget()
        self.field_expression.setEnabled(False)
        self.field_expression.setFilters(QgsFieldProxyModel.Filter.Numeric)
        generation_layout.addWidget(self.field_expression)

        points_layout = QHBoxLayout()
        points_label = QLabel("Number of Points:")
        self.num_points_spin = QSpinBox()
        self.num_points_spin.setRange(1, 10000)
        self.num_points_spin.setValue(10)
        points_layout.addWidget(points_label)
        points_layout.addWidget(self.num_points_spin)
        generation_layout.addLayout(points_layout)

        layout.addWidget(generation_group)

        self.generate_button = QPushButton("Generate Points")
        layout.addWidget(self.generate_button)

        self.start_slider.valueChanged.connect(self.start_spin.setValue)
        self.start_spin.valueChanged.connect(self.start_slider.setValue)
        self.end_slider.valueChanged.connect(self.end_spin.setValue)
        self.end_spin.valueChanged.connect(self.end_slider.setValue)
        self.start_slider.valueChanged.connect(self.slider1_changed)
        self.end_slider.valueChanged.connect(self.slider2_changed)
        self.mirror_checkbox.stateChanged.connect(self.mirror_changed)
        self.reset_button.clicked.connect(self.reset_sliders)
        self.dynamic_point_checkbox.stateChanged.connect(self.update_field_expression_state)
        self.generate_button.clicked.connect(self.generate_points)
        self.layer_combo.layerChanged.connect(self.field_expression.setLayer)
        self.layer_combo.layerChanged.connect(self.update_widget_state)

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(420, 540)

    @staticmethod
    def _is_line_layer(layer):
        if not isinstance(layer, QgsVectorLayer):
            return False
        if layer.geometryType() == Qgis.GeometryType.Line:
            return True
        return QgsWkbTypes.geometryType(layer.wkbType()) == Qgis.GeometryType.Line

    def _line_layers_in_project(self):
        return [
            layer for layer in QgsProject.instance().mapLayers().values()
            if self._is_line_layer(layer)
        ]

    def _has_usable_line_layer(self):
        current = self.layer_combo.currentLayer()
        if current and self._is_line_layer(current):
            return True
        return bool(self._line_layers_in_project())

    def _default_line_layer(self):
        """Prefer the first visible line layer in the tree, otherwise any line layer."""
        for node in QgsProject.instance().layerTreeRoot().findLayers():
            layer = node.layer()
            if node.isVisible() and self._is_line_layer(layer):
                return layer
        line_layers = self._line_layers_in_project()
        return line_layers[0] if line_layers else None

    def enable_widgets(self):
        """Enable all interactive widgets."""
        self.layer_combo.setEnabled(True)
        self.selected_features_checkbox.setEnabled(True)
        self.start_slider.setEnabled(True)
        self.start_spin.setEnabled(True)
        self.end_slider.setEnabled(True)
        self.end_spin.setEnabled(True)
        self.mirror_checkbox.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.dynamic_point_checkbox.setEnabled(True)
        self.num_points_spin.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.seed_spin.setEnabled(True)
        self.min_distance_spin.setEnabled(True)
        self.update_field_expression_state(self.dynamic_point_checkbox.checkState())

    def update_widget_state(self, *_args):
        """Enable or disable widgets based on available line layers."""
        if self._has_usable_line_layer():
            self.warning_shown = False
            self.enable_widgets()

            default_layer = self._default_line_layer()
            if default_layer and not self.layer_combo.currentLayer():
                self.layer_combo.setLayer(default_layer)
            return

        self.disable_widgets()
        if not self.warning_shown:
            self.iface.messageBar().pushMessage(
                "Warning",
                "No line layers found in the project. Add a line layer to use this tool.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            self.warning_shown = True

    def mirror_changed(self, state):
        """Handle changes in the mirror checkbox state."""
        self.mirroring = state == Qt.CheckState.Checked
        if self.mirroring:
            value = self.start_slider.value()
            self.end_slider.blockSignals(True)
            self.end_spin.blockSignals(True)
            self.end_slider.setValue(value)
            self.end_spin.setValue(value)
            self.end_slider.blockSignals(False)
            self.end_spin.blockSignals(False)
        else:
            self.start_slider.setMaximum(100)
            self.end_slider.setMaximum(100)
            self.start_spin.setMaximum(100)
            self.end_spin.setMaximum(100)

    def slider1_changed(self, value):
        """Handle changes in the left-to-right slider."""
        if self.mirroring:
            self.end_slider.blockSignals(True)
            self.end_spin.blockSignals(True)
            self.end_slider.setValue(value)
            self.end_spin.setValue(value)
            self.end_slider.blockSignals(False)
            self.end_spin.blockSignals(False)
        else:
            start_pos = value
            end_pos = 100 - self.end_slider.value()

            if start_pos > end_pos:
                new_end_value = 100 - start_pos
                self.end_slider.blockSignals(True)
                self.end_spin.blockSignals(True)
                self.end_slider.setValue(new_end_value)
                self.end_spin.setValue(new_end_value)
                self.end_slider.blockSignals(False)
                self.end_spin.blockSignals(False)

    def slider2_changed(self, value):
        """Handle changes in the right-to-left slider."""
        if self.mirroring:
            self.start_slider.blockSignals(True)
            self.start_spin.blockSignals(True)
            self.start_slider.setValue(value)
            self.start_spin.setValue(value)
            self.start_slider.blockSignals(False)
            self.start_spin.blockSignals(False)
        else:
            start_pos = self.start_slider.value()
            end_pos = 100 - value

            if end_pos < start_pos:
                self.start_slider.blockSignals(True)
                self.start_spin.blockSignals(True)
                self.start_slider.setValue(end_pos)
                self.start_spin.setValue(end_pos)
                self.start_slider.blockSignals(False)
                self.start_spin.blockSignals(False)

    def reset_sliders(self):
        """Reset both sliders to their default values."""
        self.start_slider.setValue(0)
        self.start_spin.setValue(0)
        self.end_slider.setValue(0)
        self.end_spin.setValue(0)

    def update_field_expression_state(self, state):
        """Enable or disable the field expression widget based on dynamic point generation state."""
        checked = state == Qt.CheckState.Checked
        self.field_expression.setEnabled(checked)
        self.num_points_spin.setEnabled(not checked)

    def generate_random_points(self, line, num_points):
        """Generate random points along a given line geometry."""
        if self.seed_spin.value() >= 0:
            random.seed(self.seed_spin.value())

        points = []
        length = line.length()
        min_distance = length * (self.start_slider.value() / 100)
        max_distance = length * (1 - (self.end_slider.value() / 100))

        attempts = 0
        max_attempts = 1000
        min_dist = self.min_distance_spin.value()

        while len(points) < num_points and attempts < max_attempts:
            distance = random.uniform(min_distance, max_distance)
            point = line.interpolate(distance)
            point_xy = point.asPoint()

            if min_dist > 0:
                too_close = False
                for existing_point, _ in points:
                    if point_xy.distance(existing_point) < min_dist:
                        too_close = True
                        break
                if too_close:
                    attempts += 1
                    continue

            points.append((point_xy, distance))
            attempts = 0

        if len(points) < num_points:
            self.iface.messageBar().pushMessage(
                "Warning",
                f"Could only generate {len(points)} points while maintaining minimum distance of {min_dist}",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )

        return points

    def validate_expression(self):
        """Validate that the field expression returns a numeric value."""
        if not self.dynamic_point_checkbox.isChecked():
            return True

        layer = self.layer_combo.currentLayer()
        if not layer:
            return False

        expression = QgsExpression(self.field_expression.currentText())
        if expression.hasParserError():
            self.iface.messageBar().pushMessage(
                "Warning",
                "Invalid expression: " + expression.parserErrorString(),
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return False

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))

        for feature in layer.getFeatures():
            context.setFeature(feature)
            value = expression.evaluate(context)

            if value is None:
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "Expression returns no value",
                    level=Qgis.MessageLevel.Warning,
                    duration=5,
                )
                return False

            if not isinstance(value, (int, float)) or value <= 0:
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "Expression must return a positive number",
                    level=Qgis.MessageLevel.Warning,
                    duration=5,
                )
                return False

            break

        return True

    def generate_points(self):
        """Generate points based on user selection."""
        if not self.validate_expression():
            return

        layer = self.layer_combo.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage(
                "Warning",
                "Please select a line layer first.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            return

        crs = layer.crs()
        random_points_layer = QgsVectorLayer("Point", "Random Points", "memory")
        random_points_layer.setCrs(crs)

        pr = random_points_layer.dataProvider()
        pr.addAttributes([
            QgsField("ID", QMetaType.Type.Int),
            QgsField("Distance", QMetaType.Type.Double),
            QgsField("XCoord", QMetaType.Type.Double),
            QgsField("YCoord", QMetaType.Type.Double),
            QgsField("CRSXCoord", QMetaType.Type.Double),
            QgsField("CRSYCoord", QMetaType.Type.Double),
        ])
        random_points_layer.updateFields()
        random_points_layer.startEditing()

        unique_id = 1

        if self.selected_features_checkbox.isChecked():
            features = layer.selectedFeatures()
            if not features:
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "No features selected.",
                    level=Qgis.MessageLevel.Warning,
                    duration=5,
                )
                return
        else:
            features = layer.getFeatures()

        if self.dynamic_point_checkbox.isChecked():
            expression = QgsExpression(self.field_expression.currentText())
            context = QgsExpressionContext()
            context.appendScope(QgsExpressionContextUtils.layerScope(layer))

            for feature in features:
                context.setFeature(feature)
                num_points = expression.evaluate(context)
                if num_points:
                    random_points = self.generate_random_points(
                        feature.geometry(), int(num_points)
                    )
                    for point, distance in random_points:
                        point_feature = QgsFeature()
                        point_feature.setGeometry(
                            QgsGeometry.fromPointXY(QgsPointXY(point))
                        )
                        x_coord = point.x()
                        y_coord = point.y()
                        point_feature.setAttributes([
                            unique_id, distance, x_coord, y_coord, x_coord, y_coord
                        ])
                        unique_id += 1
                        pr.addFeatures([point_feature])
        else:
            num_points = self.num_points_spin.value()
            for feature in features:
                random_points = self.generate_random_points(
                    feature.geometry(), num_points
                )
                for point, distance in random_points:
                    point_feature = QgsFeature()
                    point_feature.setGeometry(
                        QgsGeometry.fromPointXY(QgsPointXY(point))
                    )
                    x_coord = point.x()
                    y_coord = point.y()
                    point_feature.setAttributes([
                        unique_id, distance, x_coord, y_coord, x_coord, y_coord
                    ])
                    unique_id += 1
                    pr.addFeatures([point_feature])

        random_points_layer.commitChanges()
        QgsProject.instance().addMapLayer(random_points_layer)
        iface.mapCanvas().refresh()

    def show_help(self):
        """Show help dialog with instructions."""
        help_path = os.path.join(os.path.dirname(__file__), "help_content.txt")
        with open(help_path, encoding="utf-8") as help_file:
            help_text = self.DIALOG_TITLE + "\n\n" + help_file.read()

        help_dlg = QDialog(self.iface.mainWindow())
        help_dlg.setWindowTitle(self.DIALOG_TITLE)
        layout = QtWidgets.QVBoxLayout(help_dlg)
        text_edit = QtWidgets.QPlainTextEdit()
        text_edit.setPlainText(help_text)
        text_edit.setReadOnly(True)
        text_edit.setMinimumSize(520, 420)
        layout.addWidget(text_edit)
        btn = QtWidgets.QPushButton("Close")
        btn.clicked.connect(help_dlg.accept)
        layout.addWidget(btn)
        help_dlg.exec()

    def disable_widgets(self):
        """Disable all widgets."""
        self.layer_combo.setEnabled(False)
        self.selected_features_checkbox.setEnabled(False)
        self.start_slider.setEnabled(False)
        self.start_spin.setEnabled(False)
        self.end_slider.setEnabled(False)
        self.end_spin.setEnabled(False)
        self.mirror_checkbox.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.dynamic_point_checkbox.setEnabled(False)
        self.field_expression.setEnabled(False)
        self.num_points_spin.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.seed_spin.setEnabled(False)
        self.min_distance_spin.setEnabled(False)

    def cancel(self):
        """Triggered when Cancel button is clicked."""
        self.closingPlugin.emit()

    def showEvent(self, event):
        """Refresh widget state each time the dialog is shown."""
        super().showEvent(event)
        self.update_widget_state()

    def closeEvent(self, event):
        event.accept()
        self.hide()
        self.closingPlugin.emit()


def show_dialog(iface):
    dialog = RandomPointsDialog(iface)
    dialog.show()
    return dialog
