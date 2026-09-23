import 'dart:convert';

import 'package:flutter/services.dart' show AssetBundle, rootBundle;

/// Path of the bundled catalog. Every sheet path inside it is also bundle-relative.
const String catalogAssetPath = 'assets/characters/characters.json';

/// One sprite-sheet clip: where the sheet is and how its frames are laid out.
///
/// Frames are row-major (left to right, then top to bottom); cells past
/// [frameCount] are empty.
class AnimationDef {
  const AnimationDef({
    required this.key,
    required this.sheet,
    required this.frameWidth,
    required this.frameHeight,
    required this.columns,
    required this.rows,
    required this.frameCount,
    required this.fps,
    required this.loop,
  });

  factory AnimationDef.fromJson(String key, Map<String, dynamic> json) {
    final def = AnimationDef(
      key: key,
      sheet: _string(json, 'sheet', key),
      frameWidth: _int(json, 'frameWidth', key),
      frameHeight: _int(json, 'frameHeight', key),
      columns: _int(json, 'columns', key),
      rows: _int(json, 'rows', key),
      frameCount: _int(json, 'frameCount', key),
      fps: _int(json, 'fps', key),
      loop: json['loop'] == true,
    );
    if (def.frameWidth <= 0 ||
        def.frameHeight <= 0 ||
        def.columns <= 0 ||
        def.rows <= 0 ||
        def.fps <= 0) {
      throw FormatException('animation "$key": sizes, grid and fps must be > 0');
    }
    if (def.frameCount <= 0 || def.frameCount > def.columns * def.rows) {
      throw FormatException(
        'animation "$key": frameCount must be 1..${def.columns * def.rows}',
      );
    }
    return def;
  }

  final String key;
  final String sheet;
  final int frameWidth;
  final int frameHeight;
  final int columns;
  final int rows;
  final int frameCount;
  final int fps;
  final bool loop;

  /// Button text: the JSON key with its first letter capitalized.
  String get label => key[0].toUpperCase() + key.substring(1);

  /// How long one play-through lasts.
  Duration get duration =>
      Duration(microseconds: frameCount * Duration.microsecondsPerSecond ~/ fps);
}

/// A character's optional special attack: an effect sprite that flies from
/// attacker to target, and a one-shot impact played on arrival.
class SkillDef {
  const SkillDef({
    required this.name,
    this.spin = false,
    required this.animation,
    required this.impact,
  });

  factory SkillDef.fromJson(Map<String, dynamic> json, String owner) {
    final name = _string(json, 'name', owner);
    final animationRaw = json['animation'];
    if (animationRaw is! Map<String, dynamic>) {
      throw FormatException('character "$owner": skill "animation" must be an object');
    }
    final impactRaw = json['impact'];
    if (impactRaw is! Map<String, dynamic>) {
      throw FormatException('character "$owner": skill "impact" must be an object');
    }
    final impact = AnimationDef.fromJson('impact', impactRaw);
    if (impact.loop) {
      throw FormatException('character "$owner": skill "impact" must not loop');
    }
    final spinRaw = json['spin'];
    if (spinRaw != null && spinRaw is! bool) {
      throw FormatException('character "$owner": skill "spin" must be a boolean');
    }
    return SkillDef(
      name: name,
      spin: spinRaw == true,
      animation: AnimationDef.fromJson('skill', animationRaw),
      impact: impact,
    );
  }

  final String name;

  /// Whether the flying effect sprite spins continuously in flight.
  final bool spin;
  final AnimationDef animation;
  final AnimationDef impact;
}

class CharacterDef {
  const CharacterDef({
    required this.id,
    required this.name,
    required this.idle,
    required this.actions,
    this.skill,
  });

  factory CharacterDef.fromJson(Map<String, dynamic> json) {
    final id = _string(json, 'id', 'character');
    final raw = json['animations'];
    if (raw is! Map<String, dynamic>) {
      throw FormatException('character "$id": "animations" must be an object');
    }
    AnimationDef? idle;
    final actions = <AnimationDef>[];
    for (final entry in raw.entries) {
      final value = entry.value;
      if (value is! Map<String, dynamic>) {
        throw FormatException('character "$id": animation "${entry.key}" must be an object');
      }
      final def = AnimationDef.fromJson(entry.key, value);
      if (entry.key == 'idle') {
        idle = def;
      } else {
        actions.add(def);
      }
    }
    if (idle == null) {
      throw FormatException('character "$id": an "idle" animation is required');
    }
    final skillRaw = json['skill'];
    SkillDef? skill;
    if (skillRaw != null) {
      if (skillRaw is! Map<String, dynamic>) {
        throw FormatException('character "$id": "skill" must be an object');
      }
      skill = SkillDef.fromJson(skillRaw, id);
    }
    return CharacterDef(
      id: id,
      name: _string(json, 'name', id),
      idle: idle,
      actions: actions,
      skill: skill,
    );
  }

  final String id;
  final String name;
  final AnimationDef idle;

  /// Every non-idle animation, in the order the JSON listed them. "hurt" is
  /// an ordinary entry here like any other, not special-cased.
  final List<AnimationDef> actions;

  /// The character's special attack, or null if it has none.
  final SkillDef? skill;

  /// Finds an action by its key. Never matches "idle", which isn't in
  /// [actions].
  AnimationDef? byKey(String key) {
    for (final action in actions) {
      if (action.key == key) return action;
    }
    return null;
  }
}

/// Parses the catalog JSON text into characters, in file order.
List<CharacterDef> parseCatalog(String jsonText) {
  final root = jsonDecode(jsonText);
  if (root is! Map<String, dynamic>) {
    throw const FormatException('catalog root must be an object');
  }
  final list = root['characters'];
  if (list == null) return const [];
  if (list is! List) {
    throw const FormatException('"characters" must be an array');
  }
  return [
    for (final item in list)
      if (item is Map<String, dynamic>)
        CharacterDef.fromJson(item)
      else
        throw const FormatException('each character must be an object'),
  ];
}

/// Loads and parses the bundled catalog.
Future<List<CharacterDef>> loadCatalog({AssetBundle? bundle}) async {
  final text = await (bundle ?? rootBundle).loadString(catalogAssetPath);
  return parseCatalog(text);
}

String _string(Map<String, dynamic> json, String field, String owner) {
  final value = json[field];
  if (value is String && value.isNotEmpty) return value;
  throw FormatException('"$owner": "$field" must be a non-empty string');
}

int _int(Map<String, dynamic> json, String field, String owner) {
  final value = json[field];
  if (value is int) return value;
  if (value is num && value == value.roundToDouble()) return value.toInt();
  throw FormatException('"$owner": "$field" must be an integer');
}
