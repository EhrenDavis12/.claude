import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart' show AssetBundle, rootBundle;
import 'package:flutter/material.dart' show CircularProgressIndicator;
import 'package:flutter/widgets.dart';

import 'character_catalog.dart';

/// Decodes each sheet once and hands out the same [ui.Image] to every user.
class SheetCache {
  SheetCache({AssetBundle? bundle}) : _bundle = bundle;

  final AssetBundle? _bundle;
  final Map<String, Future<ui.Image>> _pending = {};
  final Map<String, ui.Image> _ready = {};

  /// The decoded sheet, or null if it has not finished decoding yet.
  ui.Image? peek(String path) => _ready[path];

  Future<ui.Image> load(String path) {
    final ready = _ready[path];
    if (ready != null) return Future.value(ready);
    return _pending.putIfAbsent(path, () {
      final future = _decode(path);
      future.then(
        (image) => _ready[path] = image,
        // Drop a failed decode so a later attempt can retry.
        onError: (Object _) => _pending.remove(path),
      );
      return future;
    });
  }

  /// Seeds an already-decoded image (used by tests).
  void put(String path, ui.Image image) {
    _ready[path] = image;
    _pending.remove(path);
  }

  Future<ui.Image> _decode(String path) async {
    final data = await (_bundle ?? rootBundle).load(path);
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
    try {
      return (await codec.getNextFrame()).image;
    } finally {
      codec.dispose();
    }
  }
}

/// Plays one [AnimationDef] from its sheet, driven by a [Ticker].
///
/// Looping clips wrap; one-shot clips hold their last frame and fire
/// [onFinished] once. Changing [animation] or bumping [playId] restarts
/// playback from frame 0.
class SpritePlayer extends StatefulWidget {
  const SpritePlayer({
    super.key,
    required this.animation,
    required this.sheets,
    this.playId = 0,
    this.onFinished,
  });

  final AnimationDef animation;
  final SheetCache sheets;
  final int playId;
  final VoidCallback? onFinished;

  @override
  State<SpritePlayer> createState() => SpritePlayerState();
}

class SpritePlayerState extends State<SpritePlayer>
    with SingleTickerProviderStateMixin {
  late final Ticker _ticker;

  /// The frame currently shown. Only the painter listens to it, so a frame
  /// change repaints the sprite without rebuilding any widget.
  final ValueNotifier<int> frame = ValueNotifier<int>(0);

  ui.Image? _image;
  Object? _error;
  bool _finished = false;
  int _loadId = 0;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker(_onTick);
    _load();
  }

  @override
  void didUpdateWidget(SpritePlayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.animation.sheet != widget.animation.sheet ||
        oldWidget.sheets != widget.sheets) {
      _load();
    } else if (oldWidget.animation != widget.animation ||
        oldWidget.playId != widget.playId) {
      _restart();
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    frame.dispose();
    super.dispose();
  }

  void _load() {
    final id = ++_loadId;
    _ticker.stop();
    _error = null;
    _finished = false;
    frame.value = 0;
    final cached = widget.sheets.peek(widget.animation.sheet);
    if (cached != null) {
      _image = cached;
      _ticker.start();
      return;
    }
    _image = null;
    widget.sheets.load(widget.animation.sheet).then(
      (image) {
        if (!mounted || id != _loadId) return;
        setState(() => _image = image);
        _restart();
      },
      onError: (Object error) {
        if (!mounted || id != _loadId) return;
        setState(() => _error = error);
      },
    );
  }

  void _restart() {
    _ticker.stop();
    _finished = false;
    frame.value = 0;
    if (_image != null) _ticker.start();
  }

  void _onTick(Duration elapsed) {
    final anim = widget.animation;
    final raw =
        (elapsed.inMicroseconds * anim.fps) ~/ Duration.microsecondsPerSecond;
    int index;
    if (anim.loop) {
      index = raw % anim.frameCount;
    } else if (raw >= anim.frameCount) {
      index = anim.frameCount - 1;
      if (!_finished) {
        _finished = true;
        _ticker.stop();
        widget.onFinished?.call();
      }
    } else {
      index = raw;
    }
    if (index != frame.value) frame.value = index;
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    if (error != null) return _SheetError(widget.animation.sheet, error);
    final image = _image;
    if (image == null) return const _Loading();
    return RepaintBoundary(
      child: SizedBox.expand(
        child: CustomPaint(
          painter: SpriteFramePainter(
            image: image,
            animation: widget.animation,
            frame: frame,
          ),
        ),
      ),
    );
  }
}

/// Draws one fixed frame of an animation (the carousel thumbnail).
class SpriteFrame extends StatelessWidget {
  const SpriteFrame({
    super.key,
    required this.animation,
    required this.sheets,
    this.frameIndex = 0,
  });

  final AnimationDef animation;
  final SheetCache sheets;
  final int frameIndex;

  @override
  Widget build(BuildContext context) {
    final cached = sheets.peek(animation.sheet);
    if (cached != null) return _paint(cached);
    return FutureBuilder<ui.Image>(
      future: sheets.load(animation.sheet),
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return _SheetError(animation.sheet, snapshot.error!);
        }
        final image = snapshot.data;
        if (image == null) return const _Loading();
        return _paint(image);
      },
    );
  }

  Widget _paint(ui.Image image) {
    return SizedBox.expand(
      child: CustomPaint(
        painter: SpriteFramePainter(
          image: image,
          animation: animation,
          frame: ValueNotifier<int>(frameIndex),
        ),
      ),
    );
  }
}

/// Paints the cell for `frame.value`, fitted (`contain`) and centered.
class SpriteFramePainter extends CustomPainter {
  SpriteFramePainter({
    required this.image,
    required this.animation,
    required this.frame,
  }) : super(repaint: frame);

  final ui.Image image;
  final AnimationDef animation;
  final ValueListenable<int> frame;

  static final Paint _paint = Paint()..filterQuality = FilterQuality.medium;

  @override
  void paint(Canvas canvas, Size size) {
    final index = frame.value.clamp(0, animation.frameCount - 1);
    final fw = animation.frameWidth.toDouble();
    final fh = animation.frameHeight.toDouble();
    final src = Rect.fromLTWH(
      (index % animation.columns) * fw,
      (index ~/ animation.columns) * fh,
      fw,
      fh,
    );
    final scale = math.min(size.width / fw, size.height / fh);
    final dw = fw * scale;
    final dh = fh * scale;
    final dst = Rect.fromLTWH((size.width - dw) / 2, (size.height - dh) / 2, dw, dh);
    canvas.drawImageRect(image, src, dst, _paint);
  }

  @override
  bool shouldRepaint(SpriteFramePainter old) =>
      old.image != image || old.animation != animation || old.frame != frame;
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: SizedBox(
        width: 24,
        height: 24,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
    );
  }
}

class _SheetError extends StatelessWidget {
  const _SheetError(this.path, this.error);

  final String path;
  final Object error;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Text(
          'Could not load $path\n$error',
          textAlign: TextAlign.center,
          style: const TextStyle(color: Color(0xFFFF7B7B), fontSize: 12),
        ),
      ),
    );
  }
}
