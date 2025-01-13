import os
import random

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                               QSpinBox, QDialogButtonBox, QComboBox, QCheckBox, 
                               QStyle, QStyleOptionSlider, QHBoxLayout, QGridLayout,
                               QGroupBox)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsFieldExpressionWidget
from qgis.core import (QgsMapLayerProxyModel, QgsVectorLayer, QgsFeature, 
                      QgsGeometry, QgsPointXY, QgsWkbTypes, QgsProject,
                      QgsFieldProxyModel, QgsLayerTreeLayer, QgsMapLayer, QgsField, QgsExpression)
from qgis.PyQt.QtCore import Qt, QVariant, QRect, pyqtSignal
from qgis.PyQt.QtGui import QPainter, QPalette
from PyQt5 import QtWidgets
from qgis.utils import iface
from qgis.core import QgsExpressionContext, QgsExpressionContextUtils

class RandomPointsDialog(QDialog):
    closingPlugin = pyqtSignal()  # Define the closingPlugin signal

    def __init__(self, iface):
        """Constructor."""
        super(RandomPointsDialog, self).__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle('Random Points Along Line')
        
        # Initialize variables
        self.warning_shown = False
        self.mirroring = False
        
        # Setup UI
        self.setup_ui()
        
        # Initialize
        self.setDefaultLayer()
        self.check_line_layers()
        
        # Connect to project signals
        QgsProject.instance().layersAdded.connect(self.check_line_layers)
        QgsProject.instance().layersRemoved.connect(self.check_line_layers)

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Help Button
        help_layout = QHBoxLayout()
        help_button = QPushButton()
        help_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        help_button.setToolTip("Click for help")
        help_button.clicked.connect(self.show_help)
        help_layout.addStretch()
        help_layout.addWidget(help_button)
        layout.addLayout(help_layout)
        
        # Layer Selection Group
        layer_group = QGroupBox("Layer Selection")
        layer_layout = QVBoxLayout()
        layer_group.setLayout(layer_layout)
        
        # Layer combo
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        layer_layout.addWidget(self.layer_combo)
        
        # Checkbox for using only selected features
        self.selected_features_checkbox = QCheckBox("Use only selected features")
        self.selected_features_checkbox.setChecked(False)  # Default is unchecked
        layer_layout.addWidget(self.selected_features_checkbox)
        
        layout.addWidget(layer_group)
        
        # Offset Settings Group
        offset_group = QGroupBox("Offset Settings")
        offset_layout = QVBoxLayout()
        offset_group.setLayout(offset_layout)
        
        # Start slider
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Offset (%)")
        self.start_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.start_slider.setRange(0, 100)
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 100)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_slider)
        start_layout.addWidget(self.start_spin)
        offset_layout.addLayout(start_layout)
        
        # End slider
        end_layout = QHBoxLayout()
        end_label = QLabel("End Offset (%)")
        self.end_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.end_slider.setRange(0, 100)
        self.end_slider.setInvertedAppearance(True)
        self.end_spin = QSpinBox()
        self.end_spin.setRange(0, 100)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_slider)
        end_layout.addWidget(self.end_spin)
        offset_layout.addLayout(end_layout)
        
        # Mirror checkbox and reset button
        mirror_reset_layout = QHBoxLayout()
        self.mirror_checkbox = QCheckBox("Mirror")
        self.mirror_checkbox.setChecked(False)
        self.reset_button = QPushButton("Reset Offsets")
        mirror_reset_layout.addWidget(self.mirror_checkbox)
        mirror_reset_layout.addWidget(self.reset_button)
        offset_layout.addLayout(mirror_reset_layout)
        
        layout.addWidget(offset_group)
        
        # Point Generation Settings Group
        generation_group = QGroupBox("Point Generation Settings")
        generation_layout = QVBoxLayout()
        generation_group.setLayout(generation_layout)
        
        # Random Seed
        seed_layout = QHBoxLayout()
        seed_label = QLabel("Random Seed:")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 999999)
        self.seed_spin.setValue(-1)
        self.seed_spin.setToolTip("Set a seed for reproducible results (-1 for random)")
        seed_layout.addWidget(seed_label)
        seed_layout.addWidget(self.seed_spin)
        generation_layout.addLayout(seed_layout)
        
        # Minimum Distance
        min_dist_layout = QHBoxLayout()
        min_dist_label = QLabel("Min. Distance:")
        self.min_distance_spin = QtWidgets.QDoubleSpinBox()
        self.min_distance_spin.setRange(0, 999999)
        self.min_distance_spin.setValue(0)
        self.min_distance_spin.setToolTip("Minimum distance between points (0 for no minimum)")
        min_dist_layout.addWidget(min_dist_label)
        min_dist_layout.addWidget(self.min_distance_spin)
        generation_layout.addLayout(min_dist_layout)
        
        # Dynamic point generation
        self.dynamic_point_checkbox = QCheckBox("Use Field for Dynamic Point Generation")
        self.dynamic_point_checkbox.setChecked(False)
        generation_layout.addWidget(self.dynamic_point_checkbox)
        
        # Field expression widget
        self.field_expression = QgsFieldExpressionWidget()
        self.field_expression.setEnabled(False)
        self.field_expression.setFilters(QgsFieldProxyModel.Numeric)  # Only allow numeric fields
        generation_layout.addWidget(self.field_expression)
        
        # Number of points
        points_layout = QHBoxLayout()
        points_label = QLabel("Number of Points:")
        self.num_points_spin = QSpinBox()
        self.num_points_spin.setRange(1, 10000)
        self.num_points_spin.setValue(10)
        points_layout.addWidget(points_label)
        points_layout.addWidget(self.num_points_spin)
        generation_layout.addLayout(points_layout)
        
        layout.addWidget(generation_group)
        
        # Generate button
        self.generate_button = QPushButton("Generate Points")
        layout.addWidget(self.generate_button)

        # Connect signals
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

        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.resize(420, 540)  # Set initial size to 420x540 pixels

    def setDefaultLayer(self):
        """Sets the default layer to the first visible line layer."""
        if not QgsProject.instance().layerTreeRoot().children():  # Check if no project is open
            self.disable_widgets()  # Disable all widgets
            return
        layers = QgsProject.instance().layerTreeRoot().children()
        visible_line_layers = [
            layer.layer() for layer in layers 
            if isinstance(layer, QgsLayerTreeLayer) 
            and layer.isVisible() 
            and isinstance(layer.layer(), QgsVectorLayer) 
            and layer.layer().geometryType() == QgsWkbTypes.LineGeometry
        ]

        # Disable relevant widgets if no line layers are available
        if not visible_line_layers:
            self.layer_combo.setEnabled(False)
            self.selected_features_checkbox.setEnabled(False)
            self.start_slider.setEnabled(False)
            self.start_spin.setEnabled(False)
            self.end_slider.setEnabled(False)
            self.end_spin.setEnabled(False)
            self.mirror_checkbox.setEnabled(False)
            self.reset_button.setEnabled(False)
            self.dynamic_point_checkbox.setEnabled(False)
            self.num_points_spin.setEnabled(False)
            self.generate_button.setEnabled(False)
            self.seed_spin.setEnabled(False)  # Disable
            self.min_distance_spin.setEnabled(False)  # Disable

        else:
            # Enable widgets when line layers are available
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
            self.seed_spin.setEnabled(True)  # Enabled
            self.min_distance_spin.setEnabled(True)  # Enabled
            self.layer_combo.setLayer(visible_line_layers[0])

    def mirror_changed(self, state):
        """Handle changes in the mirror checkbox state."""
        self.mirroring = state == Qt.Checked
        if state == Qt.Checked:
            # When checked, set both sliders to the same value
            value = self.start_slider.value()
            self.end_slider.blockSignals(True)
            self.end_spin.blockSignals(True)
            self.end_slider.setValue(value)
            self.end_spin.setValue(value)
            self.end_slider.blockSignals(False)
            self.end_spin.blockSignals(False)
        else:
            # Allow full range when mirror is unchecked
            self.start_slider.setMaximum(100)
            self.end_slider.setMaximum(100)
            self.start_spin.setMaximum(100)
            self.end_spin.setMaximum(100)

    def slider1_changed(self, value):
        """Handle changes in the left-to-right slider."""
        if self.mirroring:
            # When mirroring is enabled, set slider2 to the same value
            self.end_slider.blockSignals(True)
            self.end_spin.blockSignals(True)
            self.end_slider.setValue(value)
            self.end_spin.setValue(value)
            self.end_slider.blockSignals(False)
            self.end_spin.blockSignals(False)
        else:
            # Get the current positions
            start_pos = value
            end_pos = 100 - self.end_slider.value()  # Convert from inverted to normal scale
            
            # If start slider is pushing into end slider's space
            if start_pos > end_pos:
                # Push the end slider
                new_end_value = 100 - start_pos  # Convert back to inverted scale
                self.end_slider.blockSignals(True)
                self.end_spin.blockSignals(True)
                self.end_slider.setValue(new_end_value)
                self.end_spin.setValue(new_end_value)
                self.end_slider.blockSignals(False)
                self.end_spin.blockSignals(False)

    def slider2_changed(self, value):
        """Handle changes in the right-to-left slider."""
        if self.mirroring:
            # When mirroring is enabled, set slider1 to the same value
            self.start_slider.blockSignals(True)
            self.start_spin.blockSignals(True)
            self.start_slider.setValue(value)
            self.start_spin.setValue(value)
            self.start_slider.blockSignals(False)
            self.start_spin.blockSignals(False)
        else:
            # Get the current positions
            start_pos = self.start_slider.value()
            end_pos = 100 - value  # Convert from inverted to normal scale
            
            # If end slider is pushing into start slider's space
            if end_pos < start_pos:
                # Push the start slider
                new_start_value = end_pos
                self.start_slider.blockSignals(True)
                self.start_spin.blockSignals(True)
                self.start_slider.setValue(new_start_value)
                self.start_spin.setValue(new_start_value)
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
        self.field_expression.setEnabled(state == Qt.Checked)
        if state == Qt.Checked:
            self.num_points_spin.setEnabled(False)  # Disable spin box if field expression is checked
        else:
            self.num_points_spin.setEnabled(True)  # Enable spin box if field expression is unchecked

    def generate_random_points(self, line, num_points):
        """Generate random points along a given line geometry."""
        if self.seed_spin.value() >= 0:
            random.seed(self.seed_spin.value())
            
        points = []
        length = line.length()
        min_distance = length * (self.start_slider.value() / 100)
        max_distance = length * (1 - (self.end_slider.value() / 100))
        
        # Generate points with minimum distance constraint
        attempts = 0
        max_attempts = 1000  # Prevent infinite loop
        min_dist = self.min_distance_spin.value()
        
        while len(points) < num_points and attempts < max_attempts:
            distance = random.uniform(min_distance, max_distance)
            point = line.interpolate(distance)
            point_xy = point.asPoint()
            
            # Check minimum distance constraint
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
            attempts = 0  # Reset attempts counter after successful point
            
        if len(points) < num_points:
            QtWidgets.QMessageBox.warning(
                self, 
                "Warning", 
                f"Could only generate {len(points)} points while maintaining minimum distance of {min_dist}"
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
            QtWidgets.QMessageBox.warning(self, "Warning", "Invalid expression: " + expression.parserErrorString())
            return False
            
        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        
        # Test with first feature
        for feature in layer.getFeatures():
            context.setFeature(feature)
            value = expression.evaluate(context)
            
            if value is None:
                QtWidgets.QMessageBox.warning(self, "Warning", "Expression returns no value")
                return False
                
            if not isinstance(value, (int, float)) or value <= 0:
                QtWidgets.QMessageBox.warning(self, "Warning", "Expression must return a positive number")
                return False
                
            break
            
        return True

    def generate_points(self):
        """Generate points based on user selection"""
        if not self.validate_expression():
            return
            
        layer = self.layer_combo.currentLayer()
        if not layer:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a line layer first.")
            return

        # Create a new memory layer for the points
        crs = layer.crs()
        random_points_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", "Random Points", "memory")
        
        pr = random_points_layer.dataProvider()
        pr.addAttributes([
            QgsField("ID", QVariant.Int),
            QgsField("Distance", QVariant.Double),
            QgsField("XCoord", QVariant.Double),
            QgsField("YCoord", QVariant.Double),
            QgsField("CRSXCoord", QVariant.Double),
            QgsField("CRSYCoord", QVariant.Double)
        ])
        random_points_layer.updateFields()
        random_points_layer.startEditing()
        
        unique_id = 1
            
        # Get features based on selection mode
        if self.selected_features_checkbox.isChecked():
            features = layer.selectedFeatures()
            if not features:
                QtWidgets.QMessageBox.warning(self, "Warning", "No features selected.")
                return
        else:
            features = layer.getFeatures()
            
        # Process features
        if self.dynamic_point_checkbox.isChecked():
            # Dynamic point generation using field expression
            expression = QgsExpression(self.field_expression.currentText())
            context = QgsExpressionContext()
            context.appendScope(QgsExpressionContextUtils.layerScope(layer))
            
            for feature in features:
                context.setFeature(feature)
                num_points = expression.evaluate(context)
                if num_points:
                    random_points = self.generate_random_points(feature.geometry(), int(num_points))
                    for point, distance in random_points:
                        point_feature = QgsFeature()
                        point_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
                        x_coord = point.x()
                        y_coord = point.y()
                        point_feature.setAttributes([unique_id, distance, x_coord, y_coord, x_coord, y_coord])
                        unique_id += 1
                        pr.addFeatures([point_feature])
        else:
            # Fixed number of points
            num_points = self.num_points_spin.value()
            for feature in features:
                random_points = self.generate_random_points(feature.geometry(), num_points)
                for point, distance in random_points:
                    point_feature = QgsFeature()
                    point_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
                    x_coord = point.x()
                    y_coord = point.y()
                    point_feature.setAttributes([unique_id, distance, x_coord, y_coord, x_coord, y_coord])
                    unique_id += 1
                    pr.addFeatures([point_feature])

        random_points_layer.commitChanges()
        QgsProject.instance().addMapLayer(random_points_layer)
        iface.mapCanvas().refresh()

    def check_line_layers(self):
        """Check for line layers in the project"""
        if not QgsProject.instance().layerTreeRoot().children():  # Check if no project is open
            self.disable_widgets()  # Disable all widgets
            return
        line_layers = [layer for layer in QgsProject.instance().mapLayers().values() 
                      if layer.type() == QgsMapLayer.VectorLayer 
                      and layer.geometryType() == QgsWkbTypes.LineGeometry]
        
        if line_layers:
            self.warning_shown = False
            # Enable widgets if line layers are available
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
            self.seed_spin.setEnabled(True)  # Enabled
            self.min_distance_spin.setEnabled(True)  # Enabled
            self.layer_combo.setLayer(line_layers[0])

    def show_help(self):
        """Show help dialog with instructions."""
        help_text = "Random Points Along Line Generator\n\nBasic Usage:\n1. Select a line layer from the dropdown\n2. Choose whether to process all features or only selected features\n3. Set the start and end offsets using the sliders\n4. Specify the number of points to generate\n\nAdvanced Features:\nOffset Settings:\n- Use the sliders to control where points can be generated along the lines\n- Start Offset: Distance from the start of the line\n- End Offset: Distance from the end of the line\n- Mirror checkbox: Synchronize both sliders\n- Reset Offsets: Return sliders to default positions\n\nPoint Generation Settings:\n- Random Seed: Controls the randomization of points\n  • -1: Different random points each time (default)\n  • 0-999999: Fixed seed that generates the same points each time\n- Min. Distance: Minimum distance between generated points (0 for no minimum)\n- Dynamic Generation: Use a field to determine the number of points per feature\n- Number of Points: Fixed number of points to generate per feature\n\nRandom Seed Explained:\nThe random seed controls how points are randomly placed along the line:\n- Using -1 (Default): Each time you generate points, they will be placed in different random positions.\n  This is useful when you want to explore different point arrangements.\n\n- Using a Fixed Seed (0-999999): Points will be placed in the exact same positions every time you\n  generate them with this seed number. This is useful when you need:\n  • Reproducible results for scientific analysis\n  • Consistent point patterns across different sessions\n  • To share exact point arrangements with colleagues\n\nExample: If you use seed = 42, the points will always be generated in the same positions as long as\nall other settings (number of points, offsets, etc.) remain the same.\n\nTips:\n- The field expression must return a numeric value when using dynamic generation\n- Points are distributed randomly within the specified line segments\n- CRS coordinates are automatically added to the output layer"
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Help")
        msg_box.setText(help_text)
        msg_box.exec_()

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
        self.seed_spin.setEnabled(False)  # Disable
        self.min_distance_spin.setEnabled(False)  # Disable
        
    def cancel(self):
        """Triggered when Cancel button is clicked."""
        # Emit signal to close plugin and uncheck toggle
        self.closingPlugin.emit()  

    def closeEvent(self, event):
        # Override close event to hide dialog instead of deleting it
        event.ignore()
        self.hide()
        self.closingPlugin.emit()  # Emit the signal to notify that the dialog is closed
        
def show_dialog(iface):
    dialog = RandomPointsDialog(iface)
    dialog.show()
    return dialog

# --- Script Execution ---
# Create and show the dialog
dialog = RandomPointsDialog(iface)