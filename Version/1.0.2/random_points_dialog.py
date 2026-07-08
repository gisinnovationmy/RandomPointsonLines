import os
import random

from qgis.PyQt import uic, QtWidgets
from qgis.core import QgsProject, QgsGeometry, QgsFeature, QgsVectorLayer, QgsPointXY, QgsWkbTypes, QgsMapLayerProxyModel, QgsField, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsSingleSymbolRenderer, QgsMarkerSymbol
from PyQt5.QtCore import Qt, QVariant
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

# Load the UI form
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'random_points_dialog_base.ui'))

class RandomPointsDialog(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(RandomPointsDialog, self).__init__(parent)
        self.setupUi(self)
        
        # Set the layer dropdown to only show line layers
        self.Layer.setFilters(QgsMapLayerProxyModel.LineLayer)

        # Connect signals
        self.OKCancelButton.accepted.connect(self.generate)
        self.OKCancelButton.rejected.connect(self.cancel)

        # Set default layer
        self.setDefaultLayer()

        # Set window to stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Make the dialog visually appealing
        self.setWindowTitle("Generate Random Points Along Lines")
        self.setFixedSize(400, 300)  # Adjusted size for a more compact, user-friendly layout

    def setDefaultLayer(self):
        """Sets the default layer to the first visible line layer."""
        layers = QgsProject.instance().layerTreeRoot().children()
        visible_line_layers = [
            layer.layer() for layer in layers
            if isinstance(layer.layer(), QgsVectorLayer) and layer.isVisible() and layer.layer().geometryType() == QgsWkbTypes.LineGeometry
        ]

        if visible_line_layers:
            # Set the first visible line layer
            self.Layer.setLayer(visible_line_layers[0])  

    def generate_random_points(self, line, num_points):
        """Generate random points along a given line geometry."""
        points = []
        length = line.length()
        for _ in range(num_points):
            # Interpolate a point at a random distance along the line
            distance = random.uniform(0, length)
            point = line.interpolate(distance)
            points.append((point.asPoint(), distance))
        return points

    def generate(self):
        """Triggered when OK button is clicked to generate random points."""
        # Get selected layer and number of random points from the dialog
        line_layer = self.Layer.currentLayer()  
        num_random_points = self.RandomPoints.value()  

        # Ensure a valid line layer is selected
        if not line_layer or not line_layer.isValid() or line_layer.geometryType() != QgsWkbTypes.LineGeometry:
            QtWidgets.QMessageBox.critical(self, "Error", "Please select a valid line layer.")
            return

        # Use the CRS of the selected line layer for the random points layer
        crs = line_layer.crs().toWkt()  # Get the CRS in WKT format
        random_points_layer = QgsVectorLayer(f"Point?crs={crs}", "Random Points", "memory")

        pr = random_points_layer.dataProvider()
        pr.addAttributes([
            QgsField("ID", QVariant.Int), 
            QgsField("Distance", QVariant.Double),
            QgsField("XCoord_", QVariant.Double),          # Easting in layer CRS
            QgsField("YCoord_", QVariant.Double),          # Northing in layer CRS
            QgsField("XCoordProjCRS", QVariant.Double),    # Easting in project CRS
            QgsField("YCoordProjCRS", QVariant.Double)     # Northing in project CRS
        ])
        random_points_layer.updateFields()
        random_points_layer.startEditing()

        # Get project CRS and set up coordinate transformation
        project_crs = QgsProject.instance().crs()
        transform = QgsCoordinateTransform(line_layer.crs(), project_crs, QgsProject.instance())

        # Initialize unique ID
        unique_id = 1  

        # Iterate over each feature in the line layer and generate random points
        for feature in line_layer.getFeatures():
            line_geom = feature.geometry()
            random_points = self.generate_random_points(line_geom, num_random_points)
            
            # Add each generated point as a feature to the layer
            for point, distance in random_points:
                point_feature = QgsFeature()
                point_feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))

                # Set attributes including Distance, XCoord_, YCoord_, XCoordProjCRS, and YCoordProjCRS
                x_coord = point.x()
                y_coord = point.y()
                distance = round(line_geom.lineLocatePoint(QgsGeometry.fromPointXY(QgsPointXY(point))), 5)

                # Transform the point to project CRS
                point_proj_crs = transform.transform(QgsPointXY(point))
                x_coord_proj = point_proj_crs.x()
                y_coord_proj = point_proj_crs.y()

                point_feature.setAttributes([unique_id, distance, x_coord, y_coord, x_coord_proj, y_coord_proj]) 
                
                # Increment ID for each point
                unique_id += 1  
                
                # Add feature to the provider
                pr.addFeatures([point_feature]) 

        # Commit changes
        random_points_layer.commitChanges()

        # Customize the appearance of the points
        symbol = QgsMarkerSymbol.createSimple({
            'color': '#db1e2a',         # Set the color to #db1e2a
            'size': '2.3',              # Set the size to 2.3
            'outline_color': '#000000', # Optional: outline color (black)
            'outline_width': '0.5'      # Optional: outline width
        })
        random_points_layer.renderer().setSymbol(symbol)

        # Add the random points layer to the map
        QgsProject.instance().addMapLayer(random_points_layer)
        iface.mapCanvas().refresh()

        # Emit signal to uncheck toggle after generating points
        self.closingPlugin.emit()

    def cancel(self):
        """Triggered when Cancel button is clicked."""
        # Emit signal to close plugin and uncheck toggle
        self.closingPlugin.emit()  

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()