// widgets.dart - the tap card (a dark card, like the app's other overlay panels) and the data-date line.
import 'dart:typed_data' show Uint8List;

import 'package:flutter/material.dart';

import 'controller.dart';
import 'models.dart';
import 'words.dart';

const _card = Color(0xEB0E1621);
const _muted = Colors.white70;
const _statusBg = {'missing': Color(0x38E21E28), 'fault': Color(0x33F59E0B), 'temporary': Color(0x408A96A3)};
const _statusEdge = {'missing': Color(0xFFE21E28), 'fault': Color(0xFFF59E0B), 'temporary': Color(0xFF8A96A3)};

/// The card for one aid: name, kind, Light List number, federal/private, the status with its date (from the
/// Local Notice to Mariners), the light (spelled out), range, height, structure, remarks, waterway, district,
/// the data date and "Not for navigation". [symbol]: the aid's symbol (PNG), shown beside the name.
class AtonCard extends StatelessWidget {
  const AtonCard({super.key, required this.feature, this.dataDate, this.onClose, this.symbol});

  /// The card from the controller (its data date and the aid's symbol).
  factory AtonCard.of(AtonFeature feature, AtonController controller, {Key? key, VoidCallback? onClose}) =>
      AtonCard(key: key, feature: feature, dataDate: controller.meta?.dataDate, onClose: onClose,
          symbol: controller.images[feature.sym]);

  final AtonFeature feature;
  final String? dataDate;
  final VoidCallback? onClose;
  final Uint8List? symbol;

  @override
  Widget build(BuildContext context) {
    final c = cardFor(feature.props, dataDate);
    const small = TextStyle(color: _muted, fontSize: 12.5);
    final status = feature.status;
    return Material(
      color: _card,
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (symbol != null)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Image.memory(symbol!, width: 34, height: 34, gaplessPlayback: true),
              ),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(c.title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(c.subtitle, style: small),
              ]),
            ),
            if (onClose != null)
              IconButton(
                onPressed: onClose,
                icon: const Icon(Icons.close, color: _muted, size: 20),
                tooltip: 'Close',
                visualDensity: VisualDensity.compact,
              ),
          ]),
          if (c.status.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 10, right: 8),
              // rounded corners by clipping: Flutter refuses a borderRadius on a one-sided Border
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                  decoration: BoxDecoration(
                    color: _statusBg[status] ?? _statusBg['fault'],
                    border: Border(left: BorderSide(color: _statusEdge[status] ?? _statusEdge['fault']!, width: 4)),
                  ),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(c.status,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13.5)),
                    if (c.statusNote.isNotEmpty) Text(c.statusNote, style: small),
                  ]),
                ),
              ),
            ),
          const SizedBox(height: 8),
          for (final (label, value) in c.rows)
            Padding(
              padding: const EdgeInsets.only(top: 3, right: 8),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 82, child: Text(label, style: small)),
                Expanded(child: Text(value, style: const TextStyle(color: Colors.white, fontSize: 13.5))),
              ]),
            ),
          if (c.unlisted.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8, right: 8),
              child: Text(c.unlisted, style: const TextStyle(color: Color(0xFFFFD38A), fontSize: 12.5)),
            ),
          Padding(
            padding: const EdgeInsets.only(top: 10, right: 8),
            child: Text(c.footer, style: const TextStyle(color: _muted, fontSize: 11.5)),
          ),
        ]),
      ),
    );
  }
}

/// Shows [AtonCard] for [feature] as a bottom sheet (e.g. from AtonMapLibre's onFeatureTapped).
Future<void> showAtonCard(BuildContext context, AtonFeature feature, AtonController controller) =>
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black12,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 0, 8, 10),
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.62),
            child: SingleChildScrollView(
                child: AtonCard.of(feature, controller, onClose: () => Navigator.of(ctx).pop())),
          ),
        ),
      ),
    );

/// The line the app shows while the overlay is on: "Buoys & lights · Coast Guard data of Oct 19, 2026 · Not for
/// navigation", plus "SAMPLE DATA" or "Coast Guard data not updated for N days" when that applies.
class AtonNote extends StatelessWidget {
  const AtonNote({super.key, required this.controller});
  final AtonController controller;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: controller,
        builder: (context, _) {
          final c = controller;
          if (!c.enabled) return const SizedBox.shrink();
          final lines = [
            if (c.meta?.sample == true) 'SAMPLE DATA: made-up aids for testing',
            if (c.staleLine != null) c.staleLine!,
            if (c.error != null && c.meta == null) c.error!,
            c.noteLine,
          ];
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(color: const Color(0xE6FFFFFF), borderRadius: BorderRadius.circular(8)),
            child: Text(lines.join('\n'), style: const TextStyle(color: Color(0xFF14202B), fontSize: 11)),
          );
        },
      );
}
