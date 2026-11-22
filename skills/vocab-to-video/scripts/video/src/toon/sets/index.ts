import { home } from "./home";
import { office } from "./office";
import { SetDef } from "./parts";
import { street } from "./street";
import { voidSet } from "./void";

/** Every place a shot can happen in. A new set is one file plus one line here and in rig.json. */
export const SETS: Record<string, SetDef> = { home, office, street, void: voidSet };
